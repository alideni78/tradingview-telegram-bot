"""Service for managing trading positions."""

from decimal import Decimal
from typing import Dict, Optional

import structlog

from ..core.exceptions import PositionNotFoundError
from ..models import Position, PositionStatus

logger = structlog.get_logger(__name__)


class PositionManager:
    """Manage trading positions in memory."""

    def __init__(self) -> None:
        """Initialize position manager."""
        self._positions: Dict[str, Position] = {}
        logger.info("position_manager_initialized")

    def has_open_position(self, symbol: str) -> bool:
        """Check if symbol has an open position.

        Args:
            symbol: Trading symbol

        Returns:
            True if position exists and is open
        """
        return symbol.upper() in self._positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position if found, None otherwise
        """
        return self._positions.get(symbol.upper())

    def add_position(self, position: Position) -> None:
        """Add a new position.

        Args:
            position: Position to add
        """
        symbol = position.symbol.upper()
        self._positions[symbol] = position
        logger.info(
            "position_added",
            symbol=symbol,
            side=position.side.value,
            entry_price=float(position.entry_price),
        )

    def close_position(
        self, symbol: str, status: PositionStatus, exit_price: Optional[Decimal] = None
    ) -> Position:
        """Close a position.

        Args:
            symbol: Trading symbol
            status: Closing status
            exit_price: Exit price (required for SL closes)

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position doesn't exist
        """
        symbol = symbol.upper()
        position = self._positions.pop(symbol, None)

        if not position:
            raise PositionNotFoundError(f"No open position for {symbol}")

        position.close(status=status, exit_price=exit_price)

        logger.info(
            "position_closed",
            symbol=symbol,
            status=status.value,
            exit_price=float(exit_price) if exit_price else None,
        )

        return position

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

    def get_all_positions(self) -> Dict[str, Position]:
        """Get all open positions.

        Returns:
            Dictionary of symbol -> Position
        """
        return self._positions.copy()

    def clear_all(self) -> None:
        """Clear all positions (for testing)."""
        count = len(self._positions)
        self._positions.clear()
        logger.info("all_positions_cleared", count=count)
