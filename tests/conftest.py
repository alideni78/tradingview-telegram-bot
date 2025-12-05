"""Pytest configuration and fixtures."""

from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.app.core.config import Settings
from src.app.main import create_app
from src.app.models import Position, PositionSide, PositionStatus
from src.app.services import PositionManager, TelegramService


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        telegram_bot_token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        telegram_chat_id="-1001234567890",
        webhook_secret="test_webhook_secret_1234567890",
        host="0.0.0.0",
        port=8000,
        debug=True,
        log_level="DEBUG",
        log_format="console",
        rate_limit_tradingview=60,
        rate_limit_telegram=30,
        environment="development",
    )


@pytest.fixture
def position_manager() -> PositionManager:
    """Create position manager instance."""
    return PositionManager()


@pytest.fixture
def sample_position(test_settings: Settings) -> Position:
    """Create sample position."""
    return Position(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        entry_price=Decimal("42150.50"),
        stop_loss=Decimal("41800.00"),
        entry_time="2025-12-05 13:30:00",
        chat_id=test_settings.telegram_chat_id,
        message_id=123,
    )


@pytest.fixture
def telegram_service(test_settings: Settings) -> TelegramService:
    """Create telegram service instance."""
    return TelegramService(test_settings)


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
