"""Tests for domain models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.app.models import Position, PositionSide, PositionStatus, Signal, SignalType


class TestPosition:
    """Test Position model."""

    def test_create_position(self) -> None:
        """Test creating a valid position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )

        assert position.symbol == "BTCUSDT"
        assert position.side == PositionSide.LONG
        assert position.status == PositionStatus.OPEN
        assert position.message_id == 0

    def test_position_symbol_uppercase(self) -> None:
        """Test symbol is converted to uppercase."""
        position = Position(
            symbol="btcusdt",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )

        assert position.symbol == "BTCUSDT"

    def test_position_invalid_price(self) -> None:
        """Test position with invalid price."""
        with pytest.raises(ValidationError):
            Position(
                symbol="BTCUSDT",
                side=PositionSide.LONG,
                entry_price=Decimal("-100"),  # Negative price
                stop_loss=Decimal("41800.00"),
                entry_time="2025-12-05 13:30:00",
                chat_id="-1001234567890",
            )

    def test_position_close(self) -> None:
        """Test closing a position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )

        position.close(PositionStatus.CLOSED_BY_SL, Decimal("41800.00"))

        assert position.status == PositionStatus.CLOSED_BY_SL
        assert position.exit_price == Decimal("41800.00")
        assert position.closed_at is not None

    def test_position_to_telegram_message_open(self) -> None:
        """Test formatting open position as Telegram message."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )

        message = position.to_telegram_message()

        assert "📊 BTCUSDT | Long" in message
        assert "⏰ Time: 2025-12-05 13:30:00" in message
        assert "💰 Entry: 42,150.50" in message
        assert "🛑 SL: 41,800.00" in message
        assert "Status: OPEN" in message

    def test_position_to_telegram_message_closed_sl(self) -> None:
        """Test formatting closed position (SL) as Telegram message."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )
        position.close(PositionStatus.CLOSED_BY_SL, Decimal("41800.00"))

        message = position.to_telegram_message()

        assert "Status: CLOSED · by reached SL at 41,800.00" in message

    def test_position_to_telegram_message_closed_reverse(self) -> None:
        """Test formatting closed position (reverse) as Telegram message."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
        )
        position.close(PositionStatus.CLOSED_BY_REVERSE)

        message = position.to_telegram_message()

        assert "Status: CLOSED · by reverse signal" in message


class TestSignal:
    """Test Signal model."""

    def test_create_buy_signal(self) -> None:
        """Test creating a BUY signal."""
        signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY_SIGNAL,
            time="2025-12-05 13:30:00",
            price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
        )

        assert signal.symbol == "BTCUSDT"
        assert signal.is_open_signal is True
        assert signal.is_stop_loss is False
        assert signal.position_side == PositionSide.LONG

    def test_create_sell_signal(self) -> None:
        """Test creating a SELL signal."""
        signal = Signal(
            symbol="ETHUSDT",
            signal_type=SignalType.SELL_SIGNAL,
            time="2025-12-05 14:00:00",
            price=Decimal("2250.75"),
            stop_loss=Decimal("2280.00"),
        )

        assert signal.is_open_signal is True
        assert signal.position_side == PositionSide.SHORT

    def test_create_stop_loss_signal(self) -> None:
        """Test creating a STOP LOSS signal."""
        signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.STOP_LOSS,
            time="2025-12-05 15:00:00",
            price=Decimal("41800.00"),
        )

        assert signal.is_stop_loss is True
        assert signal.is_open_signal is False
        assert signal.position_side is None

    def test_signal_symbol_uppercase(self) -> None:
        """Test signal symbol is converted to uppercase."""
        signal = Signal(
            symbol="btcusdt",
            signal_type=SignalType.BUY_SIGNAL,
            time="2025-12-05 13:30:00",
            price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
        )

        assert signal.symbol == "BTCUSDT"
