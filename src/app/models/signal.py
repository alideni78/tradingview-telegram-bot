"""Signal model representing a TradingView alert."""

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .position import PositionSide


class SignalType(str, Enum):
    """TradingView signal type."""

    BUY_SIGNAL = "BUY SIGNAL"
    SELL_SIGNAL = "SELL SIGNAL"
    STOP_LOSS = "STOP LOSS"


class Signal(BaseModel):
    """TradingView signal model."""

    symbol: str = Field(..., description="Trading symbol")
    signal_type: SignalType = Field(..., description="Signal type")
    time: str = Field(..., description="Signal time")
    price: Decimal = Field(..., description="Entry or exit price", gt=0)
    stop_loss: Optional[Decimal] = Field(default=None, description="Stop loss price", gt=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @property
    def is_open_signal(self) -> bool:
        """Check if signal is an open signal.

        Returns:
            True if BUY or SELL signal
        """
        return self.signal_type in (SignalType.BUY_SIGNAL, SignalType.SELL_SIGNAL)

    @property
    def is_stop_loss(self) -> bool:
        """Check if signal is a stop loss.

        Returns:
            True if STOP LOSS signal
        """
        return self.signal_type == SignalType.STOP_LOSS

    @property
    def position_side(self) -> Optional[PositionSide]:
        """Get position side from signal.

        Returns:
            PositionSide.LONG for BUY, PositionSide.SHORT for SELL, None for STOP LOSS
        """
        if self.signal_type == SignalType.BUY_SIGNAL:
            return PositionSide.LONG
        elif self.signal_type == SignalType.SELL_SIGNAL:
            return PositionSide.SHORT
        return None

    class Config:
        """Pydantic config."""

        use_enum_values = False
        json_encoders = {
            Decimal: lambda v: float(v),
        }
