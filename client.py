import json
import threading
import getpass
import time
import httpx

BASE_URL = "http://localhost:8000"
_state = {"token": "", "prompt": ""}
_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(f"\r{msg}")
        if _state["prompt"]:
            print(_state["prompt"], end="", flush=True)


def register():
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    r = httpx.post(f"{BASE_URL}/register", json={"username": username, "password": password})
    print(r.json().get("message", r.text))


def login() -> bool:
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    r = httpx.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if r.status_code != 200:
        print("Login failed:", r.json().get("detail", r.text))
        return False
    _state["token"] = r.json()["access_token"]
    print("Logged in successfully.")
    return True


MAX_RETRIES = 5
RETRY_BASE_DELAY = 1  # seconds


def listen_for_messages():
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            headers = {"Authorization": f"Bearer {_state['token']}"}
            with httpx.stream("GET", f"{BASE_URL}/stream", headers=headers, timeout=None) as r:
                attempt = 0  # reset on successful connection
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        raw = line[len("data:"):].strip()
                        if not raw:
                            continue
                        try:
                            msg = json.loads(raw)
                            safe_print(f"[{msg['sender']} -> {msg['recipient']}]: {msg['content']}")
                        except (json.JSONDecodeError, KeyError):
                            pass
        except Exception as e:
            attempt += 1
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            safe_print(f"[Stream disconnected: {e}. Retrying in {delay}s... ({attempt}/{MAX_RETRIES})]")
            time.sleep(delay)
    safe_print("[Stream: max retries reached. No longer listening for messages.]")


def send_message(recipient: str, content: str):
    headers = {"Authorization": f"Bearer {_state['token']}"}
    r = httpx.post(
        f"{BASE_URL}/messages",
        json={"recipient": recipient, "content": content},
        headers=headers,
    )
    if r.status_code != 201:
        print("Error:", r.json().get("detail", r.text))


def main():
    print("1. Register\n2. Login")
    choice = input("Choice: ").strip()
    if choice == "1":
        register()
        print("Now login:")
    if not login():
        return

    threading.Thread(target=listen_for_messages, daemon=True).start()

    while True:
        _state["prompt"] = "To (or 'exit'): "
        recipient = input(_state["prompt"]).strip()
        _state["prompt"] = ""
        if recipient.lower() == "exit":
            break
        _state["prompt"] = "Message: "
        message = input(_state["prompt"]).strip()
        _state["prompt"] = ""
        if message:
            send_message(recipient, message)


if __name__ == "__main__":
    main()
