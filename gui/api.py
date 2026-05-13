import json
import time
import threading
import httpx

BASE_URL = "http://localhost:8000"
MAX_RETRIES = 5
RETRY_BASE_DELAY = 1

_state = {"token": "", "username": ""}


def register(username: str, password: str) -> str:
    try:
        r = httpx.post(f"{BASE_URL}/register", json={"username": username, "password": password})
        return r.json().get("message") or r.json().get("detail", r.text)
    except httpx.ConnectError:
        return "Cannot connect to server. Is it running?"


def login(username: str, password: str) -> str | None:
    """Returns error string on failure, None on success."""
    try:
        r = httpx.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    except httpx.ConnectError:
        return "Cannot connect to server. Is it running?"
    if r.status_code != 200:
        return r.json().get("detail", r.text)
    _state["token"] = r.json()["access_token"]
    _state["username"] = username
    return None


def send_message(recipient: str, content: str) -> str | None:
    """Returns error string on failure, None on success."""
    try:
        r = httpx.post(
            f"{BASE_URL}/messages",
            json={"recipient": recipient, "content": content},
            headers={"Authorization": f"Bearer {_state['token']}"},
        )
    except httpx.ConnectError:
        return "Cannot connect to server."
    if r.status_code != 201:
        return r.json().get("detail", r.text)
    return None


def start_listener(on_message, on_status):
    """Starts SSE listener in a daemon thread.
    on_message(sender, recipient, content) — called for each message.
    on_status(text)                        — called for connection events.
    """
    def _listen():
        attempt = 0
        while attempt < MAX_RETRIES:
            try:
                headers = {"Authorization": f"Bearer {_state['token']}"}
                with httpx.stream("GET", f"{BASE_URL}/stream", headers=headers, timeout=None) as r:
                    attempt = 0
                    on_status("Connected to stream.")
                    for line in r.iter_lines():
                        if line.startswith("data:"):
                            raw = line[len("data:"):].strip()
                            if not raw:
                                continue
                            try:
                                msg = json.loads(raw)
                                on_message(msg["sender"], msg["recipient"], msg["content"])
                            except (json.JSONDecodeError, KeyError):
                                pass
            except Exception as e:
                attempt += 1
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                on_status(f"Disconnected: {e}. Retry {attempt}/{MAX_RETRIES} in {delay}s...")
                time.sleep(delay)
        on_status("Max retries reached. Stream stopped.")

    threading.Thread(target=_listen, daemon=True).start()
