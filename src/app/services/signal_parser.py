"""Parse TradingView alert messages."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog

from ..core.exceptions import SignalParseError
from ..models import Signal, SignalType, PositionSide

logger = structlog.get_logger(__name__)


class SignalParser:
    """Parse TradingView webhook alert messages."""

    @staticmethod
    def parse(message: str) -> Signal:
        """Parse alert message into Signal object.

        Args:
            message: Alert message text

        Returns:
            Signal object

        Raises:
            SignalParseError: If message format is invalid
        """
        try:
            lines = [line.strip() for line in message.strip().split("\n") if line.strip()]

            if not lines:
                raise SignalParseError("Empty message")

            # Parse symbol and signal type from first line
            first_line = lines[0]
            
            # Extract symbol (before the dash)
            symbol_match = re.search(r"^([A-Z0-9.]+)", first_line)
            if not symbol_match:
                raise SignalParseError(f"Could not parse symbol from: {first_line}")
            
            symbol = symbol_match.group(1)
            # Remove .P suffix (Perpetual contracts)
            symbol = symbol.replace(".P", "")

            # Extract signal type (after the dash)
            if " - " not in first_line:
                raise SignalParseError(f"Invalid format, expected 'SYMBOL - SIGNAL': {first_line}")

            signal_text = first_line.split(" - ", 1)[1].strip().upper()

            # Ignore TP (Take Profit) signals
            if "_TP" in signal_text or "TAKE PROFIT" in signal_text or "TAKE_PROFIT" in signal_text:
                raise SignalParseError(f"Take Profit signals are not supported: {signal_text}")

            # Determine signal type
            if "BUY" in signal_text or "LONG" in signal_text:
                signal_type = SignalType.BUY_SIGNAL
            elif "SELL" in signal_text or "SHORT" in signal_text:
                signal_type = SignalType.SELL_SIGNAL
            elif "STOP" in signal_text and "LOSS" in signal_text:
                signal_type = SignalType.STOP_LOSS
            else:
                raise SignalParseError(f"Unknown signal type: {signal_text}")

            # Parse remaining fields
            time_str: Optional[str] = None
            price: Optional[Decimal] = None
            stop_loss: Optional[Decimal] = None

            for line in lines[1:]:
                if "Time:" in line or "time:" in line.lower():
                    time_str = line.split(":", 1)[1].strip()
                elif "Entry Price:" in line or "entry price:" in line.lower():
                    price_str = line.split(":", 1)[1].strip().replace(",", "")
                    try:
                        price = Decimal(price_str)
                    except Exception as e:
                        raise SignalParseError(f"Invalid entry price: {price_str}") from e
                elif "Exit Price:" in line or "exit price:" in line.lower():
                    price_str = line.split(":", 1)[1].strip().replace(",", "")
                    try:
                        price = Decimal(price_str)
                    except Exception as e:
                        raise SignalParseError(f"Invalid exit price: {price_str}") from e
                elif "Stop Loss:" in line or "stop loss:" in line.lower():
                    sl_str = line.split(":", 1)[1].strip().replace(",", "")
                    try:
                        stop_loss = Decimal(sl_str)
                    except Exception as e:
                        raise SignalParseError(f"Invalid stop loss: {sl_str}") from e

            # Validate required fields
            if signal_type != SignalType.STOP_LOSS:
                if price is None:
                    raise SignalParseError("Entry price is required for BUY/SELL signals")
                if stop_loss is None:
                    raise SignalParseError("Stop loss is required for BUY/SELL signals")
            else:
                if price is None:
                    raise SignalParseError("Exit price is required for STOP LOSS signals")

            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                time=time_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                price=price,
                stop_loss=stop_loss,
            )

            logger.info(
                "signal_parsed",
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                entry_price=float(signal.price) if signal.price else None,
            )

            return signal

        except SignalParseError:
            raise
        except Exception as e:
            logger.error("signal_parse_error", error=str(e), message=message)
            raise SignalParseError(f"Failed to parse signal: {str(e)}") from e
