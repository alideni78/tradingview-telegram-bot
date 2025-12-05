"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram Bot API token")
    telegram_chat_id: str = Field(..., description="Default Telegram chat ID")

    # Webhook Security
    webhook_secret: str = Field(..., description="Webhook secret for TradingView")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port", ge=1, le=65535)
    debug: bool = Field(default=False, description="Debug mode")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "console"] = Field(
        default="json", description="Log format (json for production, console for dev)"
    )

    # Rate Limiting (requests per minute)
    rate_limit_tradingview: int = Field(default=60, description="Rate limit for TradingView", ge=1)
    rate_limit_telegram: int = Field(default=30, description="Rate limit for Telegram", ge=1)

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="production", description="Environment name"
    )

    @field_validator("telegram_bot_token")
    @classmethod
    def validate_telegram_token(cls, v: str) -> str:
        """Validate Telegram bot token format."""
        if not v or len(v) < 40:
            raise ValueError("Invalid Telegram bot token")
        return v

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, v: str) -> str:
        """Validate webhook secret strength."""
        if not v or len(v) < 16:
            raise ValueError("Webhook secret must be at least 16 characters")
        return v

    @property
    def telegram_base_url(self) -> str:
        """Get Telegram API base URL."""
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance loaded from environment
    """
    return Settings()  # type: ignore
