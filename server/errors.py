"""
errors.py — Application-specific exception hierarchy.

Every exception carries a clear, contextual message so that logs and HTTP
responses are unambiguous without extra string-building at the call site.
"""


class AppError(Exception):
    """Base class for all application-level exceptions."""


class UserAlreadyExistsError(AppError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username '{username}' is already taken")
        self.username = username


class AuthenticationError(AppError):
    def __init__(self, reason: str = "Invalid username or password") -> None:
        super().__init__(reason)


class AuthorizationError(AppError):
    def __init__(self, reason: str = "You are not authorised to perform this action") -> None:
        super().__init__(reason)


class MessageDeliveryError(AppError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Message delivery failed: {reason}")


class ValidationError(AppError):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Validation error on '{field}': {reason}")
        self.field = field
