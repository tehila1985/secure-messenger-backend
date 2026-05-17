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
│   ├── main.py          # App entry point, router registration
│   ├── routes.py        # All API route handlers
│   ├── models.py        # SQLAlchemy database models (User, Message)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # Password hashing + JWT logic
│   ├── crypto.py        # AES-256-GCM encrypt/decrypt
│   └── broadcaster.py   # SSE pub/sub broadcaster
├── gui/
│   ├── index.html       # Browser chat UI
│   └── app.js           # Frontend logic
├── tests/
│   └── test_app.py      # Pytest test suite
├── requirements.txt
└── run.bat              # Windows quick-start script
```

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 1.1. Optional configuration

Copy `.env.example` to `.env` and customize the values if you want to override defaults such as `SECRET_KEY`, `DATABASE_URL`, or `ENCRYPTION_KEY`.

### 2. Start the server

```bash
uvicorn server.main:app --reload
```

Or on Windows, double-click `run.bat`.

### 3. Open the app

Navigate to [http://localhost:8000](http://localhost:8000)

Interactive API docs available at [http://localhost:8000/docs](http://localhost:8000/docs)

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

---

## Running Tests

```bash
pytest tests/ -v
```

---

## What's Stored in the Database

| Table    | Column          | Stored value              | Readable by attacker? |
|----------|-----------------|---------------------------|-----------------------|
| users    | username        | `alice`                   | Yes (not secret)      |
| users    | password_hash   | `$2b$12$...`              | No — one-way hash     |
| messages | sender          | `alice`                   | Yes (not secret)      |
| messages | recipient       | `bob`                     | Yes (not secret)      |
| messages | ciphertext      | `aGVsbG8gd29ybGQ...`      | No — AES encrypted    |
