"""Tests for PositionManager service."""

from decimal import Decimal

import pytest

from src.app.core.exceptions import PositionNotFoundError
from src.app.models import Position, PositionSide, PositionStatus
from src.app.services import PositionManager


class TestPositionManager:
    """Test PositionManager service."""

    def test_add_position(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test adding a position."""
        position_manager.add_position(sample_position)

        assert position_manager.has_open_position("BTCUSDT")
        stored = position_manager.get_position("BTCUSDT")
        assert stored is not None
        assert stored.symbol == "BTCUSDT"
        assert stored.side == PositionSide.LONG

    def test_get_position_case_insensitive(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test getting position is case insensitive."""
        position_manager.add_position(sample_position)

        assert position_manager.get_position("btcusdt") is not None
        assert position_manager.get_position("BTCUSDT") is not None
        assert position_manager.get_position("BtcUsDt") is not None

    def test_has_open_position(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test checking if position exists."""
        assert not position_manager.has_open_position("BTCUSDT")
        
        position_manager.add_position(sample_position)
        
        assert position_manager.has_open_position("BTCUSDT")
        assert not position_manager.has_open_position("ETHUSDT")

    def test_close_position(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test closing a position."""
        position_manager.add_position(sample_position)

        closed = position_manager.close_position(
            "BTCUSDT",
            PositionStatus.CLOSED_BY_SL,
            Decimal("41800.00")
        )

        assert closed.status == PositionStatus.CLOSED_BY_SL
        assert closed.exit_price == Decimal("41800.00")
        assert closed.closed_at is not None
        assert not position_manager.has_open_position("BTCUSDT")

    def test_close_nonexistent_position(self, position_manager: PositionManager) -> None:
        """Test closing nonexistent position raises error."""
        with pytest.raises(PositionNotFoundError, match="No open position for BTCUSDT"):
            position_manager.close_position("BTCUSDT", PositionStatus.CLOSED_MANUALLY)

    def test_handle_reverse_signal(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test handling reverse signal."""
        position_manager.add_position(sample_position)

        closed = position_manager.handle_reverse_signal("BTCUSDT")

        assert closed.status == PositionStatus.CLOSED_BY_REVERSE
        assert closed.exit_price is None
        assert not position_manager.has_open_position("BTCUSDT")

    def test_handle_stop_loss(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test handling stop loss."""
        position_manager.add_position(sample_position)

        exit_price = Decimal("41800.00")
        closed = position_manager.handle_stop_loss("BTCUSDT", exit_price)

        assert closed.status == PositionStatus.CLOSED_BY_SL
        assert closed.exit_price == exit_price
        assert not position_manager.has_open_position("BTCUSDT")

    def test_get_all_positions(self, position_manager: PositionManager) -> None:
        """Test getting all positions."""
        pos1 = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            entry_price=Decimal("42150.50"),
            stop_loss=Decimal("41800.00"),
            entry_time="2025-12-05 13:30:00",
            chat_id="-1001234567890",
            message_id=123,
        )
        pos2 = Position(
            symbol="ETHUSDT",
            side=PositionSide.SHORT,
            entry_price=Decimal("2250.75"),
            stop_loss=Decimal("2280.00"),
            entry_time="2025-12-05 14:00:00",
            chat_id="-1001234567890",
            message_id=124,
        )

        position_manager.add_position(pos1)
        position_manager.add_position(pos2)

        all_positions = position_manager.get_all_positions()
        assert len(all_positions) == 2
        assert "BTCUSDT" in all_positions
        assert "ETHUSDT" in all_positions

    def test_clear_all(self, position_manager: PositionManager, sample_position: Position) -> None:
        """Test clearing all positions."""
        position_manager.add_position(sample_position)
        assert len(position_manager.get_all_positions()) == 1

        position_manager.clear_all()
        assert len(position_manager.get_all_positions()) == 0
