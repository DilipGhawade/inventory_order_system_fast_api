from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import time
from typing import Any
import uuid

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import structlog

from app.api.deps import DBSessionDep
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup verification and graceful shutdown of async resources."""
    logger.info(
        "application_startup",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_verified")
    except Exception as exc:
        logger.error("database_startup_check_failed", error=str(exc))

    yield

    logger.info("application_shutdown_initiated")
    await engine.dispose()
    logger.info("database_engine_disposed")


def create_application() -> FastAPI:
    """Factory function constructing and configuring the FastAPI application."""
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else f"{settings.API_V1_STR}/openapi.json"

    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    @application.middleware("http")
    async def request_context_and_security_headers(
        request: Request,
        call_next: Any,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        logger.info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get(
        "/health",
        tags=["Health"],
        summary="Readiness probe verifying API and PostgreSQL connectivity",
    )
    async def health_check(db: DBSessionDep) -> JSONResponse:
        try:
            await db.execute(text("SELECT 1"))
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "healthy",
                    "database": "connected",
                    "environment": settings.ENVIRONMENT,
                    "version": settings.VERSION,
                },
            )
        except Exception as exc:
            logger.error("health_check_failed", error=str(exc))
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "database": "disconnected",
                    "environment": settings.ENVIRONMENT,
                    "version": settings.VERSION,
                },
            )

    return application


app = create_application()