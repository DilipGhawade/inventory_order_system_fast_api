from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base exception for all custom application domain errors."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APPLICATION_ERROR",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.headers = headers


class EntityNotFoundError(AppError):
    """Raised when a requested database entity does not exist."""

    def __init__(self, detail: str = "Requested resource was not found.") -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
        )


class ConflictError(AppError):
    """Raised when an operation conflicts with existing state or unique constraints."""

    def __init__(self, detail: str = "Resource conflict detected.") -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
        )


class InsufficientStockError(AppError):
    """Raised when an order requests more units than available in stock."""

    def __init__(self, detail: str = "Insufficient stock for one or more products.") -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INSUFFICIENT_STOCK",
        )


class AuthenticationError(AppError):
    """Raised when authentication credentials or tokens are invalid."""

    def __init__(self, detail: str = "Could not validate credentials.") -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(AppError):
    """Raised when an authenticated user lacks sufficient privileges."""

    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI instance."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "domain_exception",
            error_code=exc.error_code,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "path": request.url.path,
                }
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        sanitized_errors: list[dict[str, Any]] = []
        for err in exc.errors():
            sanitized_errors.append(
                {
                    "loc": [str(item) for item in err.get("loc", [])],
                    "msg": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
            )
        logger.info(
            "validation_error",
            path=request.url.path,
            method=request.method,
            errors=sanitized_errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload validation failed.",
                    "details": sanitized_errors,
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        logger.error(
            "database_integrity_error",
            path=request.url.path,
            method=request.method,
            error=str(exc.orig) if exc.orig else str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "DATABASE_INTEGRITY_ERROR",
                    "message": "A database constraint was violated (e.g., duplicate record).",
                    "path": request.url.path,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "unhandled_server_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "path": request.url.path,
                }
            },
        )