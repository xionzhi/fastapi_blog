"""Business errors translated to HTTP responses at the application boundary."""


class ApplicationError(Exception):
    """An expected failure with a stable public error code."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.headers = headers or {}


class NotFoundError(ApplicationError):
    def __init__(self, message: str, *, code: str = "resource.not_found") -> None:
        super().__init__(message, code=code, status_code=404)


class ConflictError(ApplicationError):
    def __init__(self, message: str, *, code: str = "resource.conflict") -> None:
        super().__init__(message, code=code, status_code=409)


class AuthenticationError(ApplicationError):
    def __init__(self, message: str = "Please sign in") -> None:
        super().__init__(message, code="auth.unauthorized", status_code=401)


class RateLimitError(ApplicationError):
    def __init__(self, message: str, *, retry_after: int = 900) -> None:
        super().__init__(
            message,
            code="auth.rate_limited",
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
