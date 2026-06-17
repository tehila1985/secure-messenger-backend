import base64
import hashlib
import os
import secrets
from pathlib import Path


class Settings:
    """
    Central configuration.  All values come from environment variables so that
    nothing sensitive is ever hard-coded in source.  A random SECRET_KEY is
    generated at startup when the variable is absent (safe for development;
    tokens issued in one process are invalid after a restart — acceptable in dev).
    """

    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./messenger.db")
        self.secret_key: str = os.getenv("SECRET_KEY") or secrets.token_hex(32)
        self.token_expire_hours: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))
        self.algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
        self.gui_dir: Path = Path(__file__).resolve().parent.parent / "gui"

    @property
    def encryption_key_bytes(self) -> bytes:
        if self.encryption_key:
            try:
                return base64.b64decode(self.encryption_key)
            except Exception as exc:
                raise ValueError("ENCRYPTION_KEY must be valid base64") from exc
        return hashlib.sha256(self.secret_key.encode("utf-8")).digest()


settings = Settings()
