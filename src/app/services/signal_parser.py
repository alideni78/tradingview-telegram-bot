"""Service for parsing TradingView alert messages."""

import re
from decimal import Decimal
from typing import Optional

import structlog

from ..core.exceptions import SignalParseError
from ..models import Signal, SignalType

logger = structlog.get_logger(__name__)


class SignalParser:
    """Parse TradingView alert messages into Signal objects."""

    # Regex patterns for signal detection
    OPEN_PATTERN = re.compile(r"([A-Z]+)\s*-\s*(BUY SIGNAL|SELL SIGNAL)", re.IGNORECASE)
    STOP_LOSS_PATTERN = re.compile(r"([A-Z]+)\s*-\s*STOP LOSS", re.IGNORECASE)

    # Patterns for extracting data fields
    TIME_PATTERN = re.compile(r"Time:\s*(.+)", re.IGNORECASE)
    ENTRY_PRICE_PATTERN = re.compile(r"Entry Price:\s*([\d,]+\.?\d*)", re.IGNORECASE)
    EXIT_PRICE_PATTERN = re.compile(r"Exit Price:\s*([\d,]+\.?\d*)", re.IGNORECASE)
    STOP_LOSS_VALUE_PATTERN = re.compile(r"Stop Loss:\s*([\d,]+\.?\d*)", re.IGNORECASE)

    @classmethod
    def parse(cls, message: str) -> Signal:
        """Parse a TradingView alert message.

        Args:
            message: Raw alert message from TradingView

        Returns:
            Parsed Signal object

        Raises:
            SignalParseError: If message format is invalid
        """
        if not message or not message.strip():
            raise SignalParseError("Empty message")

        message = message.strip()
        lines = message.split("\n")

        # Try to detect signal type
        open_match = cls.OPEN_PATTERN.search(lines[0])
        stop_loss_match = cls.STOP_LOSS_PATTERN.search(lines[0])

        if open_match:
            return cls._parse_open_signal(message, open_match)
        elif stop_loss_match:
            return cls._parse_stop_loss(message, stop_loss_match)
        else:
            logger.warning("unknown_signal_format", message=message[:100])
            raise SignalParseError(f"Unknown signal format: {lines[0]}")

    @classmethod
    def _parse_open_signal(cls, message: str, match: re.Match) -> Signal:  # type: ignore
        """Parse OPEN signal (BUY or SELL).

        Args:
            message: Full message
            match: Regex match object

        Returns:
            Signal object

        Raises:
            SignalParseError: If required fields are missing
        """
        symbol = match.group(1).upper()
        signal_type_str = match.group(2).upper()

        # Map signal type
        if "BUY" in signal_type_str:
            signal_type = SignalType.BUY_SIGNAL
        elif "SELL" in signal_type_str:
            signal_type = SignalType.SELL_SIGNAL
        else:
            raise SignalParseError(f"Invalid signal type: {signal_type_str}")

        # Extract required fields
        time = cls._extract_field(message, cls.TIME_PATTERN, "Time")
        entry_price = cls._extract_price(message, cls.ENTRY_PRICE_PATTERN, "Entry Price")
        stop_loss = cls._extract_price(message, cls.STOP_LOSS_VALUE_PATTERN, "Stop Loss")

        logger.info(
            "signal_parsed",
            symbol=symbol,
            signal_type=signal_type.value,
            entry_price=float(entry_price),
        )

        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            time=time,
            price=entry_price,
            stop_loss=stop_loss,
        )

    @classmethod
    def _parse_stop_loss(cls, message: str, match: re.Match) -> Signal:  # type: ignore
        """Parse STOP LOSS signal.

        Args:
            message: Full message
            match: Regex match object

        Returns:
            Signal object

        Raises:
            SignalParseError: If required fields are missing
        """
        symbol = match.group(1).upper()

        # Extract required fields
        time = cls._extract_field(message, cls.TIME_PATTERN, "Time")
        exit_price = cls._extract_price(message, cls.EXIT_PRICE_PATTERN, "Exit Price")

        logger.info(
            "stop_loss_parsed",
            symbol=symbol,
            exit_price=float(exit_price),
        )

        return Signal(
            symbol=symbol,
            signal_type=SignalType.STOP_LOSS,
            time=time,
            price=exit_price,
            stop_loss=None,
        )

    @classmethod
    def _extract_field(cls, message: str, pattern: re.Pattern, field_name: str) -> str:  # type: ignore
        """Extract a text field from message.

        Args:
            message: Full message
            pattern: Regex pattern
            field_name: Field name for error message

        Returns:
            Extracted field value

        Raises:
            SignalParseError: If field not found
        """
        match = pattern.search(message)
        if not match:
            raise SignalParseError(f"Missing field: {field_name}")
        return match.group(1).strip()

    @classmethod
    def _extract_price(cls, message: str, pattern: re.Pattern, field_name: str) -> Decimal:  # type: ignore
        """Extract a price field from message.

        Args:
            message: Full message
            pattern: Regex pattern
            field_name: Field name for error message

        Returns:
            Extracted price as Decimal

        Raises:
            SignalParseError: If field not found or invalid format
        """
        value_str = cls._extract_field(message, pattern, field_name)
        # Remove commas from number
        value_str = value_str.replace(",", "")

        try:
            return Decimal(value_str)
        except Exception as e:
            raise SignalParseError(f"Invalid {field_name} format: {value_str}") from e
