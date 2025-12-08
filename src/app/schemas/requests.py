"""API request schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TradingViewWebhook(BaseModel):
    """TradingView webhook request body."""

    # Support both old format (message) and new format (JSON fields)
    message: Optional[str] = Field(None, description="Alert message from TradingView (old format)")
    ticker: Optional[str] = Field(None, description="Symbol/Ticker")
    signal: Optional[str] = Field(None, description="Signal type: BUY, SELL, STOP LOSS")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    time: Optional[str] = Field(None, description="Signal time")
    timenow: Optional[str] = Field(None, description="Current time")
    entry: Optional[float] = Field(None, description="Entry price")
    stopLoss: Optional[float] = Field(None, description="Stop loss price")
    takeProfit1: Optional[float] = Field(None, description="Take profit 1")
    takeProfit2: Optional[float] = Field(None, description="Take profit 2")
    takeProfit3: Optional[float] = Field(None, description="Take profit 3")
    secretKey: Optional[str] = Field(None, description="Secret key for authentication")

    def to_message_format(self) -> str:
        """Convert JSON format to message format."""
        if self.message:
            return self.message
        
        # Convert new format to old format
        ticker = self.ticker or "UNKNOWN"
        signal_type = self.signal or "UNKNOWN"
        time = self.time or self.timenow or "Unknown"
        entry = self.entry or 0
        stop_loss = self.stopLoss or 0
        
        # Map signal types
        if signal_type.upper() in ["BUY", "LONG"]:
            signal_text = "BUY SIGNAL"
        elif signal_type.upper() in ["SELL", "SHORT"]:
            signal_text = "SELL SIGNAL"
        elif signal_type.upper() in ["STOP LOSS", "SL", "STOP_LOSS"]:
            signal_text = "STOP LOSS"
            return f"{ticker} - {signal_text}\nTime: {time}\nExit Price: {entry}"
        else:
            signal_text = f"{signal_type} SIGNAL"
        
        return f"{ticker} - {signal_text}\nTime: {time}\nEntry Price: {entry}\nStop Loss: {stop_loss}"

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "BTCUSDT - BUY SIGNAL\nTime: 2025-12-05 10:30:00\nEntry Price: 42150.50\nStop Loss: 41800.00"
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
