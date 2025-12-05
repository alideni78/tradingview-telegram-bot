"""Position model representing a trading position."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PositionSide(str, Enum):
    """Trading position side."""

    LONG = "Long"
    SHORT = "Short"


class PositionStatus(str, Enum):
    """Position status."""

    OPEN = "OPEN"
    CLOSED_BY_REVERSE = "CLOSED · by reverse signal"
    CLOSED_BY_SL = "CLOSED · by reached SL at"
    CLOSED_MANUALLY = "CLOSED · manually"


class Position(BaseModel):
    """Trading position model."""

    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    side: PositionSide = Field(..., description="Position side (Long/Short)")
    entry_price: Decimal = Field(..., description="Entry price", gt=0)
    stop_loss: Decimal = Field(..., description="Stop loss price", gt=0)
    entry_time: str = Field(..., description="Entry time")
    chat_id: str = Field(..., description="Telegram chat ID")
    message_id: int = Field(default=0, description="Telegram message ID")
    status: PositionStatus = Field(default=PositionStatus.OPEN, description="Position status")
    exit_price: Optional[Decimal] = Field(default=None, description="Exit price", gt=0)
    closed_at: Optional[datetime] = Field(default=None, description="Close timestamp")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    def close(self, status: PositionStatus, exit_price: Optional[Decimal] = None) -> None:
        """Close the position.

        Args:
            status: Closing status
            exit_price: Exit price (required for SL closes)
        """
        self.status = status
        self.exit_price = exit_price
        self.closed_at = datetime.utcnow()

    def to_telegram_message(self) -> str:
        """Format position as Telegram message.

        Returns:
            Formatted message string with emojis
        """
        lines = [
            f"📊 {self.symbol} | {self.side.value}",
            f"⏰ Time: {self.entry_time}",
            f"💰 Entry: {self.entry_price:,.2f}",
            f"🛑 SL: {self.stop_loss:,.2f}",
        ]

        # Format status line
        if self.status == PositionStatus.OPEN:
            status_line = f"Status: {self.status.value}"
        elif self.status == PositionStatus.CLOSED_BY_SL and self.exit_price:
            status_line = f"Status: {self.status.value} {self.exit_price:,.2f}"
        else:
            status_line = f"Status: {self.status.value}"

        lines.append(status_line)

        return "\n".join(lines)

    class Config:
        """Pydantic config."""

        use_enum_values = False
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
        }
