"""
services.py — Business logic layer.

Design principles applied here:
  - IUserRepository / IMessageRepository are structural Protocols so that any
    object matching the interface can be injected (real SQLAlchemy repos in
    production, in-memory fakes in unit tests) without subclassing.
  - Services hold no knowledge of HTTP, JSON, or presentation format.
    Callers (routes) are responsible for building response DTOs.
  - Crypto operations stay inside the service boundary; the route layer
    receives already-decrypted plain text.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .auth import create_token, hash_password, verify_password
from .crypto import decrypt, encrypt
from .errors import AuthenticationError, UserAlreadyExistsError, ValidationError
from .models import Message, User


# ---------------------------------------------------------------------------
# Repository Protocols — the service layer depends on these, not on concrete
# SQLAlchemy classes.  Swap in a fake during unit tests with zero friction.
# ---------------------------------------------------------------------------

@runtime_checkable
class IUserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...
    def create(self, username: str, password_hash: str) -> User: ...


@runtime_checkable
class IMessageRepository(Protocol):
    def create(self, sender: str, recipient: str, ciphertext: str) -> Message: ...
    def get_for_user(self, username: str) -> list[Message]: ...


# ---------------------------------------------------------------------------
# Concrete SQLAlchemy implementations
# ---------------------------------------------------------------------------

class UserRepository:
    def __init__(self, db) -> None:  # db: Session — avoid importing Session at module level
        self._db = db

    def get_by_username(self, username: str) -> User | None:
        return self._db.query(User).filter(User.username == username).first()

    def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user


class MessageRepository:
    def __init__(self, db) -> None:
        self._db = db

    def create(self, sender: str, recipient: str, ciphertext: str) -> Message:
        message = Message(sender=sender, recipient=recipient, ciphertext=ciphertext)
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message

    def get_for_user(self, username: str) -> list[Message]:
        return (
            self._db.query(Message)
            .filter((Message.sender == username) | (Message.recipient == username) | (Message.recipient == "all"))
            .order_by(Message.created_at)
            .all()
        )


# ---------------------------------------------------------------------------
# Services — pure business logic, no HTTP/JSON concerns
# ---------------------------------------------------------------------------

class AuthService:
    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    def register_user(self, username: str, password: str) -> User:
        if self._repo.get_by_username(username):
            raise UserAlreadyExistsError(username)
        # NOTE: min-length is also enforced by the Pydantic schema (Field(min_length=6)).
        # The guard below acts as a defence-in-depth check for programmatic callers
        # that bypass the HTTP layer (e.g. seed scripts, CLI tools).
        if len(password) < 6:
            raise ValidationError("password", "must be at least 6 characters")
        return self._repo.create(username, hash_password(password))

    def authenticate(self, username: str, password: str) -> User:
        user = self._repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError()
        return user

    def create_access_token(self, username: str) -> str:
        return create_token(username)


class MessageService:
    def __init__(self, message_repository: IMessageRepository) -> None:
        self._repo = message_repository

    def send_message(self, sender: str, recipient: str, content: str) -> Message:
        return self._repo.create(sender, recipient, encrypt(content))

    def fetch_messages(self, username: str) -> list[Message]:
        return self._repo.get_for_user(username)

    def decrypt_content(self, message: Message) -> str:
        """Decrypt a single message's ciphertext.  Called by the route layer."""
        return decrypt(message.ciphertext)
