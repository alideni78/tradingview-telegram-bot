"""Tests for SignalParser service."""

import pytest
from decimal import Decimal

from src.app.core.exceptions import SignalParseError
from src.app.models import SignalType
from src.app.services import SignalParser


class TestSignalParser:
    """Test SignalParser service."""

    def test_parse_buy_signal(self) -> None:
        """Test parsing BUY SIGNAL."""
        message = """BTCUSDT - BUY SIGNAL
Time: 2025-12-05 13:30:00
Entry Price: 42,150.50
Stop Loss: 41,800.00"""

        signal = SignalParser.parse(message)

        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == SignalType.BUY_SIGNAL
        assert signal.time == "2025-12-05 13:30:00"
        assert signal.price == Decimal("42150.50")
        assert signal.stop_loss == Decimal("41800.00")
        assert signal.is_open_signal is True
        assert signal.is_stop_loss is False

    def test_parse_sell_signal(self) -> None:
        """Test parsing SELL SIGNAL."""
        message = """ETHUSDT - SELL SIGNAL
Time: 2025-12-05 14:00:00
Entry Price: 2,250.75
Stop Loss: 2,280.00"""

        signal = SignalParser.parse(message)

        assert signal.symbol == "ETHUSDT"
        assert signal.signal_type == SignalType.SELL_SIGNAL
        assert signal.time == "2025-12-05 14:00:00"
        assert signal.price == Decimal("2250.75")
        assert signal.stop_loss == Decimal("2280.00")
        assert signal.is_open_signal is True

    def test_parse_stop_loss(self) -> None:
        """Test parsing STOP LOSS signal."""
        message = """BTCUSDT - STOP LOSS
Time: 2025-12-05 15:00:00
Exit Price: 41,800.00"""

        signal = SignalParser.parse(message)

        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == SignalType.STOP_LOSS
        assert signal.time == "2025-12-05 15:00:00"
        assert signal.price == Decimal("41800.00")
        assert signal.stop_loss is None
        assert signal.is_open_signal is False
        assert signal.is_stop_loss is True

    def test_parse_lowercase_signal(self) -> None:
        """Test parsing signal with lowercase."""
        message = """btcusdt - buy signal
Time: 2025-12-05 13:30:00
Entry Price: 42150.50
Stop Loss: 41800.00"""

        signal = SignalParser.parse(message)
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == SignalType.BUY_SIGNAL

    def test_parse_without_commas(self) -> None:
        """Test parsing prices without commas."""
        message = """BTCUSDT - BUY SIGNAL
Time: 2025-12-05 13:30:00
Entry Price: 42150.50
Stop Loss: 41800.00"""

        signal = SignalParser.parse(message)
        assert signal.price == Decimal("42150.50")
        assert signal.stop_loss == Decimal("41800.00")

    def test_parse_empty_message(self) -> None:
        """Test parsing empty message."""
        with pytest.raises(SignalParseError, match="Empty message"):
            SignalParser.parse("")

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid message format."""
        message = "Invalid message format"
        
        with pytest.raises(SignalParseError, match="Unknown signal format"):
            SignalParser.parse(message)

    def test_parse_missing_time(self) -> None:
        """Test parsing message with missing time."""
        message = """BTCUSDT - BUY SIGNAL
Entry Price: 42,150.50
Stop Loss: 41,800.00"""

        with pytest.raises(SignalParseError, match="Missing field: Time"):
            SignalParser.parse(message)

    def test_parse_missing_entry_price(self) -> None:
        """Test parsing message with missing entry price."""
        message = """BTCUSDT - BUY SIGNAL
Time: 2025-12-05 13:30:00
Stop Loss: 41,800.00"""

        with pytest.raises(SignalParseError, match="Missing field: Entry Price"):
            SignalParser.parse(message)

    def test_parse_missing_stop_loss(self) -> None:
        """Test parsing message with missing stop loss."""
        message = """BTCUSDT - BUY SIGNAL
Time: 2025-12-05 13:30:00
Entry Price: 42,150.50"""

        with pytest.raises(SignalParseError, match="Missing field: Stop Loss"):
            SignalParser.parse(message)

    def test_parse_invalid_price_format(self) -> None:
        """Test parsing message with invalid price format."""
        message = """BTCUSDT - BUY SIGNAL
Time: 2025-12-05 13:30:00
Entry Price: invalid
Stop Loss: 41,800.00"""

        with pytest.raises(SignalParseError, match="Invalid Entry Price format"):
            SignalParser.parse(message)
