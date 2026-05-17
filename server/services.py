from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from .auth import create_token, hash_password, verify_password
from .crypto import decrypt, encrypt
from .errors import AuthenticationError, UserAlreadyExistsError, ValidationError
from .models import Message, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, sender: str, recipient: str, ciphertext: str) -> Message:
        message = Message(sender=sender, recipient=recipient, ciphertext=ciphertext)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_for_user(self, username: str) -> list[Message]:
        return self.db.query(Message).filter(
            (Message.sender == username) | (Message.recipient == username)
        ).order_by(Message.created_at).all()


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register_user(self, username: str, password: str) -> User:
        if self.user_repository.get_by_username(username):
            raise UserAlreadyExistsError("Username already taken")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        password_hash = hash_password(password)
        return self.user_repository.create(username, password_hash)

    def authenticate(self, username: str, password: str) -> User:
        user = self.user_repository.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        return user

    def create_access_token(self, username: str) -> str:
        return create_token(username)


class MessageService:
    def __init__(self, message_repository: MessageRepository):
        self.message_repository = message_repository

    def send_message(self, sender: str, recipient: str, content: str) -> Message:
        if not recipient:
            raise ValidationError("Recipient cannot be empty")
        ciphertext = encrypt(content)
        return self.message_repository.create(sender, recipient, ciphertext)

    def fetch_messages(self, username: str) -> list[Message]:
        return self.message_repository.get_for_user(username)

    def build_response(self, message: Message) -> dict:
        return {
            "id": message.id,
            "sender": message.sender,
            "recipient": message.recipient,
            "content": decrypt(message.ciphertext),
            "created_at": message.created_at,
        }
