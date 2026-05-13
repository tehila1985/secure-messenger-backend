const BASE = "";   // same origin — served by FastAPI
let token = "";
let me    = "";

function setStatus(msg, ok = false) {
  const el = document.getElementById("auth-status");
  el.textContent = msg;
  el.style.color = ok ? "#a6e3a1" : "#f38ba8";
}

async function doRegister() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  try {
    const r = await fetch(`${BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await r.json();
    setStatus(data.message || data.detail || "Registered!", true);
  } catch {
    setStatus("Cannot connect to server.");
  }
}

async function doLogin() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  try {
    const r = await fetch(`${BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!r.ok) {
      const data = await r.json();
      setStatus(data.detail || "Login failed.");
      return;
    }
    const data = await r.json();
    token = data.access_token;
    me    = username;
    showChat();
  } catch {
    setStatus("Cannot connect to server.");
  }
}

async function doSend() {
  const recipient = document.getElementById("to").value.trim();
  const content   = document.getElementById("msg").value.trim();
  if (!recipient) { appendMsg("Please enter a recipient.", "status"); return; }
  if (!content)   { appendMsg("Please enter a message.",   "status"); return; }

  try {
    const r = await fetch(`${BASE}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ recipient, content }),
    });
    if (r.ok) {
      document.getElementById("msg").value = "";
    } else {
      const data = await r.json();
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      appendMsg(`Error: ${detail}`, "status");
    }
  } catch {
    appendMsg("Cannot connect to server.", "status");
  }
}

function appendMsg(text, cls) {
  const log = document.getElementById("log");
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function startStream() {
  const url = `${BASE}/stream?token=${encodeURIComponent(token)}`;

  // EventSource doesn't support custom headers — pass token as query param
  // The server must accept ?token= as an alternative to Authorization header
  // Fallback: use fetch-based SSE
  fetchSSE();
}

function fetchSSE(attempt = 0) {
  const MAX = 5;
  fetch(`${BASE}/stream`, {
    headers: { "Authorization": `Bearer ${token}` },
  }).then(r => {
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) {
          reconnect(attempt);
          return;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();           // keep incomplete last line
        for (const line of lines) {
          if (line.startsWith("data:")) {
            const raw = line.slice(5).trim();
            console.log("SSE raw:", raw);
            if (!raw) continue;
            try {
              const msg = JSON.parse(raw);
              const cls = msg.sender === me ? "outgoing" : "incoming";
              appendMsg(`${msg.sender}: ${msg.content}`, cls);
            } catch(e) { console.log("SSE parse error:", e); }
          }
        }
        read();
      });
    }
    appendMsg("⚡ Connected to stream.", "status");
    read();
  }).catch(() => reconnect(attempt));

  function reconnect(n) {
    if (n >= MAX) { appendMsg("Stream stopped. Refresh to reconnect.", "status"); return; }
    const delay = 1000 * Math.pow(2, n);
    appendMsg(`⚡ Disconnected. Retrying in ${delay / 1000}s… (${n + 1}/${MAX})`, "status");
    setTimeout(() => fetchSSE(n + 1), delay);
  }
}

function showChat() {
  document.getElementById("auth").style.display = "none";
  const chat = document.getElementById("chat");
  chat.style.display = "flex";
  document.getElementById("me").textContent = me;
  startStream();
  document.getElementById("msg").focus();
}
