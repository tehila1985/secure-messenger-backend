"""
routes.py — All API route handlers.

╔══════════════════════════════════════════════╗
║  YOUR TASK: implement the four routes.       ║
╚══════════════════════════════════════════════╝

WHY A SEPARATE routes.py?
  In real projects, main.py only creates the app and wires things together.
  The actual logic lives in dedicated files — one per feature area.
  This keeps files small, focused, and easy to navigate.
  main.py imports this router and registers it with one line.

THE FOUR ROUTES YOU NEED TO IMPLEMENT:

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /register                                                      │
  │   Receives: RegisterRequest (username, password)                    │
  │   1. Check if the username is already taken → return 400 if so     │
  │   2. Hash the password (NEVER store plain text)                     │
  │   3. Save the new User to the database                              │
  │   4. Return a success message                                       │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /login                                                         │
  │   Receives: LoginRequest (username, password)                       │
  │   1. Find the user in the database → return 401 if not found       │
  │   2. Verify the password against the stored hash → 401 if wrong    │
  │   3. Create and return a JWT token                                  │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /messages                          [requires valid JWT]        │
  │   Receives: SendMessageRequest (content, recipient)                 │
  │   1. Encrypt the content with encrypt()                             │
  │   2. Save a new Message row (sender=current user, recipient=...)    │
  │   3. Return the message as MessageResponse (with decrypted content) │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ GET /messages                           [requires valid JWT]        │
  │   1. Fetch all messages from the database                           │
  │   2. Decrypt each message's ciphertext before returning             │
  │   3. Return a list of MessageResponse objects                       │
  │                                                                     │
  │   THINK ABOUT: should a user see ALL messages, or only those        │
  │   where they are the sender or recipient?                           │
  └─────────────────────────────────────────────────────────────────────┘

USEFUL IMPORTS ALREADY PROVIDED BELOW.
USEFUL PATTERN — how to query the database:
  user = db.query(User).filter(User.username == "alice").first()
  messages = db.query(Message).order_by(Message.created_at).all()

USEFUL PATTERN — how to save a new row:
  new_user = User(username="alice", password_hash="$2b$...")
  db.add(new_user)
  db.commit()
  db.refresh(new_user)   ← fills in the auto-generated id and created_at
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import require_auth
from .broadcaster import broadcaster
from .errors import AuthenticationError, UserAlreadyExistsError, ValidationError
from .models import get_db
from .schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    SendMessageRequest, MessageResponse,
)
from .services import (
    AuthService,
    MessageRepository,
    MessageService,
    UserRepository,
)
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# TODO 1 — Register a new user
# ---------------------------------------------------------------------------
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_message_repository(db: Session = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_auth_service(user_repository: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(user_repository)


def get_message_service(message_repository: MessageRepository = Depends(get_message_repository)) -> MessageService:
    return MessageService(message_repository)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        auth_service.register_user(body.username, body.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return {"message": "User created successfully"}


# ---------------------------------------------------------------------------
# TODO 2 — Login and receive a JWT token
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = auth_service.authenticate(body.username, body.password)
    except AuthenticationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = auth_service.create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}

# ---------------------------------------------------------------------------
# TODO 3 — Send a message (authenticated)
# ---------------------------------------------------------------------------
@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: SendMessageRequest,
    message_service: MessageService = Depends(get_message_service),
    username: str = Depends(require_auth),
):
    new_message = message_service.send_message(username, body.recipient, body.content)
    response_data = MessageResponse(**message_service.build_response(new_message))

    target_user = None if body.recipient == "all" else body.recipient
    await broadcaster.publish(response_data.model_dump(mode="json"), target_user=target_user)
    return response_data

# ---------------------------------------------------------------------------
# TODO 4 — Fetch messages (authenticated)
# ---------------------------------------------------------------------------
@router.get("/messages", response_model=list[MessageResponse])
def get_messages(
    message_service: MessageService = Depends(get_message_service),
    username: str = Depends(require_auth),
):
    messages = message_service.fetch_messages(username)
    return [MessageResponse(**message_service.build_response(msg)) for msg in messages]



@router.get("/stream")
async def message_stream(
    username: str = Depends(require_auth),
):
    """
    נתיב SSE שמאפשר למשתמש לקבל הודעות בזמן אמת מהתור האישי שלו.
    """
    async def event_generator():
        async with broadcaster.subscribe(username) as queue:
            while True:
                message = await queue.get()
                yield {"event": "message", "data": json.dumps(message, ensure_ascii=False)}

    return EventSourceResponse(event_generator())