# 🔐 Secure Messenger

A real-time encrypted messaging application built with FastAPI, SQLAlchemy, and Server-Sent Events (SSE).

---

## Features

- **User registration & login** with bcrypt password hashing
- **JWT authentication** on all protected routes
- **AES-256-GCM encryption** — messages are never stored as plain text
- **Real-time messaging** via Server-Sent Events (SSE)
- **Browser GUI** served directly by FastAPI

---

## Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Backend     | FastAPI + Uvicorn                 |
| Database    | SQLite + SQLAlchemy ORM           |
| Auth        | JWT (python-jose) + bcrypt        |
| Encryption  | AES-256-GCM (cryptography)        |
| Real-time   | Server-Sent Events (sse-starlette)|
| Frontend    | Vanilla HTML/CSS/JS               |

---

## Project Structure

```
├── server/
│   ├── main.py          # App entry point, lifespan, router registration
│   ├── routes.py        # HTTP route handlers + DTO construction (_to_response)
│   ├── services.py      # Business logic (AuthService, MessageService)
│   │                    # + Repository Protocols (IUserRepository, IMessageRepository)
│   │                    # + Concrete SQLAlchemy repositories
│   ├── models.py        # SQLAlchemy ORM models (User, Message)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # Password hashing + JWT logic
│   ├── crypto.py        # AES-256-GCM encrypt/decrypt
│   ├── broadcaster.py   # SSE pub/sub broadcaster (asyncio.Queue based)
│   ├── errors.py        # Typed application exception hierarchy
│   └── config.py        # Centralised settings (env-driven, no hardcoded secrets)
├── gui/
│   ├── index.html       # Browser chat UI
│   └── app.js           # Frontend logic (fetch-based SSE)
├── tests/
│   └── test_app.py      # Pytest test suite (17 tests, in-memory DB)
├── pyproject.toml       # Project metadata + pytest config
├── requirements.txt
└── run.bat              # Windows quick-start script
```

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment (optional)

Copy `.env.example` to `.env` and set your own values:

```bash
copy .env.example .env
```

Key variables:

| Variable          | Default                  | Notes                                      |
|-------------------|--------------------------|--------------------------------------------|
| `SECRET_KEY`      | random (generated once)  | **Set this in production** or tokens reset on every restart |
| `DATABASE_URL`    | `sqlite:///./messenger.db` |                                          |
| `TOKEN_EXPIRE_HOURS` | `24`                  |                                            |
| `ENCRYPTION_KEY`  | derived from SECRET_KEY  | Optional base64-encoded 32-byte key        |

> ⚠️ If `SECRET_KEY` is not set, a new random key is generated on every server start —
> all existing JWT tokens will be invalidated on restart. Always set it in production.

### 3. Start the server

**Make sure you are inside the inner project folder** (the one that contains `server/`):

```bash
cd secure-messenger-stage1-master   # if you haven't already
uvicorn server.main:app --reload
```

Or on Windows, double-click `run.bat`.

### 4. Open the app

- Chat UI → [http://localhost:8000](http://localhost:8000)
- Interactive API docs → [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

| Method | Endpoint      | Auth required | Description                        |
|--------|---------------|---------------|------------------------------------|
| POST   | `/register`   | No            | Register a new user                |
| POST   | `/login`      | No            | Login and receive a JWT token      |
| POST   | `/messages`   | Yes           | Send an encrypted message          |
| GET    | `/messages`   | Yes           | Fetch your messages (decrypted)    |
| GET    | `/stream`     | Yes           | SSE stream for real-time messages  |

---

## Architecture

The codebase follows a strict layered architecture:

```
HTTP Request
    ↓
routes.py         — HTTP concerns: validation, status codes, DTO construction
    ↓
services.py       — Business logic only (no HTTP, no JSON)
    ↓
IRepository       — Protocol interface (swappable for fakes in tests)
    ↓
models.py         — SQLAlchemy ORM / SQLite
```

Key design decisions:

- **Repository Protocols** (`IUserRepository`, `IMessageRepository`) decouple services from SQLAlchemy — inject any compatible object in tests without touching the DB.
- **No hardcoded secrets** — `config.py` reads everything from environment variables; missing `SECRET_KEY` generates a random one at startup (dev-safe, prod-unsafe by design).
- **Custom exception hierarchy** (`errors.py`) — every exception carries a typed, contextual message. No raw strings passed around.
- **DTO construction in the route layer** — `_to_response()` in `routes.py` builds `MessageResponse`; the service layer returns domain objects only.

---

## Security Design

### Passwords — bcrypt (one-way)
Passwords are never stored. Only a bcrypt fingerprint is saved.
At login, the typed password is re-hashed and compared — the original is never recovered.

### Messages — AES-256-GCM (two-way)
Messages are encrypted before being written to the database and decrypted only when returned to an authenticated user.
A fresh random nonce is generated per message, so identical messages produce different ciphertexts.

### Authentication — JWT
After login, the server issues a signed JWT token valid for 24 hours.
Every protected route validates the token without a database lookup.
Missing token → `403 Forbidden`. Invalid/expired token → `401 Unauthorized`.

---

## Running Tests

```bash
pytest tests/ -v
```

17 tests across three classes: `TestAuthentication`, `TestEncryption`, `TestMessaging`.
All tests use an **in-memory SQLite database** — no test data ever touches `messenger.db`.

---

## What's Stored in the Database

| Table    | Column          | Stored value              | Readable by attacker? |
|----------|-----------------|---------------------------|-----------------------|
| users    | username        | `alice`                   | Yes (not secret)      |
| users    | password_hash   | `$2b$12$...`              | No — one-way hash     |
| messages | sender          | `alice`                   | Yes (not secret)      |
| messages | recipient       | `bob`                     | Yes (not secret)      |
| messages | ciphertext      | `aGVsbG8gd29ybGQ...`      | No — AES encrypted    |
