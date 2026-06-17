"""
routes.py — All API route handlers.

Layer responsibilities:
  - Routes own HTTP concerns: status codes, request/response schemas, errors→HTTPExceptions.
  - Routes own DTO construction via the private _to_response() helper.
  - Business logic lives exclusively in services.py.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import require_auth
from .broadcaster import broadcaster
from .errors import AuthenticationError, UserAlreadyExistsError, ValidationError
from .models import Message, get_db
from .schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    SendMessageRequest,
    TokenResponse,
)
from .services import AuthService, MessageRepository, MessageService, UserRepository
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency factories — wire concrete repos/services via FastAPI DI
# ---------------------------------------------------------------------------

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_message_repository(db: Session = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repo)


def get_message_service(repo: MessageRepository = Depends(get_message_repository)) -> MessageService:
    return MessageService(repo)


# ---------------------------------------------------------------------------
# Private helpers — DTO construction belongs in the route layer
# ---------------------------------------------------------------------------

def _to_response(msg: Message, service: MessageService) -> MessageResponse:
    """Build a MessageResponse from a DB row, decrypting content here in the route layer."""
    return MessageResponse(
        id=msg.id,
        sender=msg.sender,
        recipient=msg.recipient,
        content=service.decrypt_content(msg),
        created_at=msg.created_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        auth_service.register_user(body.username, body.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return {"message": "User created successfully"}


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        user = auth_service.authenticate(body.username, body.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    token = auth_service.create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: SendMessageRequest,
    message_service: MessageService = Depends(get_message_service),
    username: str = Depends(require_auth),
) -> MessageResponse:
    new_message = message_service.send_message(username, body.recipient, body.content)
    response_data = _to_response(new_message, message_service)

    target_user = None if body.recipient == "all" else body.recipient
    await broadcaster.publish(response_data.model_dump(mode="json"), target_user=target_user)
    return response_data


@router.get("/messages", response_model=list[MessageResponse])
def get_messages(
    message_service: MessageService = Depends(get_message_service),
    username: str = Depends(require_auth),
) -> list[MessageResponse]:
    return [_to_response(msg, message_service) for msg in message_service.fetch_messages(username)]


@router.get("/stream")
async def message_stream(username: str = Depends(require_auth)) -> EventSourceResponse:
    """SSE endpoint — holds a persistent connection and pushes messages in real time."""

    async def event_generator():
        async with broadcaster.subscribe(username) as queue:
            while True:
                message = await queue.get()
                yield {"event": "message", "data": json.dumps(message, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
