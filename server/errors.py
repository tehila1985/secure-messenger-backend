class AppError(Exception):
    """Base class for application-specific exceptions."""


class UserAlreadyExistsError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


class MessageDeliveryError(AppError):
    pass


class ValidationError(AppError):
    pass
