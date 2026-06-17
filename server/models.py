"""
models.py — Database tables as Python classes (SQLAlchemy ORM).
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency — opens a DB session per request and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(primary_key=True, index=True)
    # String lengths match the Pydantic schema constraints (max_length=50).
    username:      Mapped[str]      = mapped_column(String(50), unique=True, index=True, nullable=False)
    # bcrypt output is always 60 characters; 200 gives comfortable headroom.
    password_hash: Mapped[str]      = mapped_column(String(200), nullable=False)
    created_at:    Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Message(Base):
    __tablename__ = "messages"

    id:         Mapped[int]      = mapped_column(primary_key=True, index=True)
    sender:     Mapped[str]      = mapped_column(String(50), index=True, nullable=False)
    recipient:  Mapped[str]      = mapped_column(String(50), index=True, nullable=False)
    # AES-GCM output is base64-encoded; Text avoids any length limit.
    ciphertext: Mapped[str]      = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


def create_tables() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
