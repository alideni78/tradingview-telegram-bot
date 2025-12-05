"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

from .api.dependencies import limiter
from .api.routes import health, tradingview
from .core.config import get_settings
from .core.logging import setup_logging
from .services import PositionManager, TelegramService

logger = structlog.get_logger(__name__)

# Global instances
position_manager: PositionManager
telegram_service: TelegramService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager.

    Args:
        app: FastAPI application

    Yields:
        None
    """
    global position_manager, telegram_service

    # Startup
    settings = get_settings()
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)
    
    logger.info(
        "application_starting",
        environment=settings.environment,
        debug=settings.debug,
    )

    # Initialize services
    position_manager = PositionManager()
    telegram_service = TelegramService(settings)

    logger.info("services_initialized")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await telegram_service.close()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title="TradingView to Telegram Bot",
        description="Production-ready trading signal notification system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred",
            },
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tradingview.router, tags=["TradingView"])

    return app


app = create_app()
