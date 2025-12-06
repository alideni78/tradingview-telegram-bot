"""Service for managing trading positions."""

from decimal import Decimal
from typing import Dict, List, Optional

import structlog

from ..core.exceptions import PositionNotFoundError
from ..models import Position, PositionSide, PositionStatus

logger = structlog.get_logger(__name__)


class PositionManager:
    """Manage trading positions in memory."""

    def __init__(self) -> None:
        """Initialize position manager."""
        self._positions: Dict[str, List[Position]] = {}
        logger.info("position_manager_initialized")

    def has_open_position(self, symbol: str) -> bool:
        """Check if symbol has an open position.

        Args:
            symbol: Trading symbol

        Returns:
            True if position exists and is open
        """
        positions = self._positions.get(symbol.upper(), [])
        return any(
            p.status in [PositionStatus.OPEN, PositionStatus.NEW_LONG, PositionStatus.NEW_SHORT]
            for p in positions
        )

    def get_open_position(self, symbol: str) -> Optional[Position]:
        """Get open position by symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Open position if found, None otherwise
        """
        positions = self._positions.get(symbol.upper(), [])
        for position in reversed(positions):
            if position.status == PositionStatus.OPEN:
                return position
        return None

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get latest position by symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position if found, None otherwise
        """
        positions = self._positions.get(symbol.upper(), [])
        return positions[-1] if positions else None

    def add_position(self, position: Position) -> None:
        """Add a new position.

        Args:
            position: Position to add
        """
        symbol = position.symbol.upper()
        if symbol not in self._positions:
            self._positions[symbol] = []
        self._positions[symbol].append(position)
        logger.info(
            "position_added",
            symbol=symbol,
            side=position.side.value,
            entry_price=float(position.entry_price),
        )

    def mark_position_as_new(self, symbol: str, side: PositionSide) -> Optional[Position]:
        """Mark current open position as NEW.

        Args:
            symbol: Trading symbol
            side: Position side to check

        Returns:
            Updated position if found, None otherwise
        """
        open_position = self.get_open_position(symbol.upper())
        if not open_position:
            return None

        if open_position.side != side:
            return None

        # Update status to NEW LONG or NEW SHORT
        open_position.status = (
            PositionStatus.NEW_LONG if side == PositionSide.LONG else PositionStatus.NEW_SHORT
        )

        logger.info(
            "position_marked_as_new",
            symbol=symbol,
            side=side.value,
            new_status=open_position.status.value,
        )

        return open_position

    def close_position(self, symbol: str, status: PositionStatus, exit_price: Optional[Decimal] = None) -> Position:
        """Close current open position.

        Args:
            symbol: Trading symbol
            status: Closing status
            exit_price: Exit price (required for SL closes)

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position doesn't exist
        """
        open_position = self.get_open_position(symbol.upper())
        if not open_position:
            raise PositionNotFoundError(f"No open position for {symbol}")

        open_position.close(status=status, exit_price=exit_price)

        logger.info(
            "position_closed",
            symbol=symbol,
            status=status.value,
            exit_price=float(exit_price) if exit_price else None,
        )

        return open_position

    def handle_reverse_signal(self, symbol: str) -> Position:
        """Handle reverse signal (close with reverse status).

        Args:
            symbol: Trading symbol

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position doesn't exist
        """
        logger.info("reverse_signal_detected", symbol=symbol)
        return self.close_position(symbol, PositionStatus.CLOSED_BY_REVERSE)

    def handle_stop_loss(self, symbol: str, exit_price: Decimal) -> Position:
        """Handle stop loss hit (close with SL status).

        Args:
            symbol: Trading symbol
            exit_price: Exit price

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position doesn't exist
        """
        logger.info("stop_loss_hit", symbol=symbol, exit_price=float(exit_price))
        return self.close_position(symbol, PositionStatus.CLOSED_BY_SL, exit_price)

    def handle_manual_close(self, symbol: str) -> Position:
        """Handle manual close via button (close with manual status).

        Args:
            symbol: Trading symbol

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position doesn't exist
        """
        logger.info("manual_close_triggered", symbol=symbol)
        return self.close_position(symbol, PositionStatus.CLOSED_MANUALLY)

    def get_all_open_positions(self) -> Dict[str, Position]:
        """Get all open positions.

        Returns:
            Dictionary of symbol -> Position
        """
        open_positions = {}
        for symbol, positions in self._positions.items():
            for position in reversed(positions):
                if position.status == PositionStatus.OPEN:
                    open_positions[symbol] = position
                    break
        return open_positions

    def clear_all(self) -> None:
        """Clear all positions (for testing)."""
        count = sum(len(positions) for positions in self._positions.values())
        self._positions.clear()
        logger.info("all_positions_cleared", count=count)
