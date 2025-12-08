"""Position manager service."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

import structlog

from ..core.exceptions import PositionNotFoundError
from ..models import Position, PositionSide, PositionStatus

logger = structlog.get_logger(__name__)


class PositionManager:
    """Manage trading positions."""

    def __init__(self) -> None:
        """Initialize position manager."""
        self._open_positions: Dict[str, Position] = {}
        logger.info("position_manager_initialized")

    def add_position(self, position: Position) -> None:
        """Add a new position.

        Args:
            position: Position to add
        """
        self._open_positions[position.symbol] = position
        logger.info(
            "position_added",
            symbol=position.symbol,
            side=position.side.value,
            entry_price=float(position.entry_price),
        )

    def get_open_position(self, symbol: str) -> Optional[Position]:
        """Get open position for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Open position if exists, None otherwise
        """
        return self._open_positions.get(symbol)

    def get_all_open_positions(self) -> Dict[str, Position]:
        """Get all open positions.

        Returns:
            Dictionary of open positions
        """
        return self._open_positions.copy()

    def has_open_position(self, symbol: str) -> bool:
        """Check if symbol has open position.

        Args:
            symbol: Trading symbol

        Returns:
            True if position exists
        """
        return symbol in self._open_positions

    def remove_position(self, symbol: str) -> None:
        """Remove position.

        Args:
            symbol: Trading symbol
        """
        if symbol in self._open_positions:
            del self._open_positions[symbol]
            logger.info("position_removed", symbol=symbol)

    def mark_position_as_new(
        self, symbol: str, side: PositionSide
    ) -> Optional[Position]:
        """Mark position as NEW LONG or NEW SHORT.

        Args:
            symbol: Trading symbol
            side: Position side

        Returns:
            Updated position if exists
        """
        position = self.get_open_position(symbol)
        if position and position.side == side:
            position.mark_as_new()
            logger.info(
                "position_marked_as_new",
                symbol=symbol,
                side=side.value,
                new_status=position.status.value,
            )
            return position
        return None

    def close_position(
        self, symbol: str, status: str, exit_price: Optional[Decimal] = None
    ) -> Position:
        """Close an open position.

        Args:
            symbol: Trading symbol
            status: Close status
            exit_price: Exit price if applicable

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position not found
        """
        open_position = self.get_open_position(symbol)
        if not open_position:
            raise PositionNotFoundError(f"No open position for {symbol}")

        # Update status based on close reason
        if status == "CLOSED · by reverse signal":
            open_position.close_by_reverse()
        elif exit_price:
            open_position.close_by_stop_loss(exit_price)
        else:
            open_position.status = PositionStatus.CLOSED_BY_REVERSE
            open_position.closed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Remove from open positions
        del self._open_positions[symbol]
        logger.info("position_closed", symbol=symbol, status=status)

        return open_position

    def handle_reverse_signal(self, symbol: str) -> Position:
        """Handle reverse signal (close existing position).

        Args:
            symbol: Trading symbol

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position not found
        """
        return self.close_position(symbol, "CLOSED · by reverse signal")

    def handle_stop_loss(self, symbol: str, exit_price: Decimal) -> Position:
        """Handle stop loss signal.

        Args:
            symbol: Trading symbol
            exit_price: Exit price

        Returns:
            Closed position

        Raises:
            PositionNotFoundError: If position not found
        """
        return self.close_position(symbol, "CLOSED · by reached SL at", exit_price)
