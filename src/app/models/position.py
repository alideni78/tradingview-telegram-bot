"""Position model."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PositionSide(str, Enum):
    """Position side enum."""

    LONG = "Long"
    SHORT = "Short"


class PositionStatus(str, Enum):
    """Position status enum."""

    OPEN = "OPEN"
    NEW_LONG = "NEW LONG"
    NEW_SHORT = "NEW SHORT"
    CLOSED_BY_REVERSE = "CLOSED · by reverse signal"
    CLOSED_BY_SL = "CLOSED · by reached SL at"


class Position(BaseModel):
    """Position model representing a trading position."""

    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    side: PositionSide = Field(..., description="Position side (Long/Short)")
    entry_price: Decimal = Field(..., description="Entry price")
    stop_loss: Decimal = Field(..., description="Stop loss price")
    entry_time: str = Field(..., description="Entry timestamp")
    chat_id: str = Field(..., description="Telegram chat ID")
    message_id: int = Field(..., description="Telegram message ID")
    status: PositionStatus = Field(
        default=PositionStatus.OPEN, description="Position status"
    )
    exit_price: Optional[Decimal] = Field(None, description="Exit price (if closed)")
    closed_at: Optional[str] = Field(None, description="Close timestamp")

    class Config:
        """Pydantic config."""

        use_enum_values = False

    def mark_as_new(self) -> None:
        """Mark position as NEW LONG or NEW SHORT."""
        if self.side == PositionSide.LONG:
            self.status = PositionStatus.NEW_LONG
        else:
            self.status = PositionStatus.NEW_SHORT

    def close_by_reverse(self) -> None:
        """Close position by reverse signal."""
        self.status = PositionStatus.CLOSED_BY_REVERSE
        self.closed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def close_by_stop_loss(self, exit_price: Decimal) -> None:
        """Close position by stop loss.

        Args:
            exit_price: Exit price when stop loss hit
        """
        self.status = PositionStatus.CLOSED_BY_SL
        self.exit_price = exit_price
        self.closed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def to_telegram_message(self) -> str:
        """Format position as Telegram message.

        Returns:
            Formatted message string with emojis
        """
        # Format prices with up to 10 decimal places, removing trailing zeros
        entry_price_str = f"{float(self.entry_price):.10f}".rstrip('0').rstrip('.')
        stop_loss_str = f"{float(self.stop_loss):.10f}".rstrip('0').rstrip('.')

        lines = [
            f"🚀 {self.symbol} | {self.side.value}",
            f"🕒 Time: {self.entry_time}",
            f"🔹 Entry: {entry_price_str}",
            f"🔹 SL: {stop_loss_str}",
        ]

        # Format status line
        if self.status in [PositionStatus.OPEN, PositionStatus.NEW_LONG, PositionStatus.NEW_SHORT]:
            status_line = f"Status: {self.status.value}"
        elif self.status == PositionStatus.CLOSED_BY_SL and self.exit_price:
            exit_price_str = f"{float(self.exit_price):.10f}".rstrip('0').rstrip('.')
            status_line = f"Status: {self.status.value} {exit_price_str}"
        else:
            status_line = f"Status: {self.status.value}"

        lines.append(status_line)

        return "\n".join(lines)
