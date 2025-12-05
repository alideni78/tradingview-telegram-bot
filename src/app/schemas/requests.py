"""API request schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TradingViewWebhook(BaseModel):
    """TradingView webhook request body."""

    message: str = Field(..., description="Alert message from TradingView")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "BTCUSDT - BUY SIGNAL\nTime: 2025-12-05 10:30:00\nEntry Price: 42,150.50\nStop Loss: 41,800.00"
            }
        }


class CallbackQuery(BaseModel):
    """Telegram callback query."""

    id: str = Field(..., description="Unique identifier for this query")
    data: Optional[str] = Field(None, description="Callback data")
    message: Optional[Dict[str, Any]] = Field(None, description="Message object")


class TelegramUpdate(BaseModel):
    """Telegram update (webhook from Telegram)."""

    update_id: int = Field(..., description="Update identifier")
    callback_query: Optional[CallbackQuery] = Field(None, description="Callback query")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "update_id": 123456789,
                "callback_query": {
                    "id": "callback_id",
                    "data": "close_BTCUSDT",
                    "message": {"chat": {"id": -1001234567890}, "message_id": 123},
                },
            }
        }
