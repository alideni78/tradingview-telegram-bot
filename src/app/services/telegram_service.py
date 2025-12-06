"""Service for interacting with Telegram Bot API."""

from typing import Optional

import httpx
import structlog

from ..core.config import Settings
from ..core.exceptions import TelegramAPIError
from ..models import Position

logger = structlog.get_logger(__name__)


class TelegramService:
    """Handle Telegram Bot API interactions."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Telegram service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.base_url = settings.telegram_base_url
        self.default_chat_id = settings.telegram_chat_id
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info("telegram_service_initialized")

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def send_position_message(
        self, 
        position: Position,
        reply_to_message_id: Optional[int] = None
    ) -> Optional[int]:
        """Send position message to Telegram.

        Args:
            position: Position to send
            reply_to_message_id: Optional message ID to reply to

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message_text = position.to_telegram_message()

            payload = {
                "chat_id": position.chat_id,
                "text": message_text,
                "parse_mode": "HTML",
            }
            
            # Add reply if specified
            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id

            response = await self.client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                message_id = result["result"]["message_id"]
                logger.info(
                    "telegram_message_sent",
                    symbol=position.symbol,
                    message_id=message_id,
                )
                return message_id
            else:
                logger.error(
                    "telegram_api_error",
                    error=result.get("description"),
                    symbol=position.symbol,
                )
                return None

        except httpx.HTTPError as e:
            logger.error(
                "telegram_http_error",
                error=str(e),
                symbol=position.symbol,
            )
            raise TelegramAPIError(f"Failed to send message: {e}") from e
        except Exception as e:
            logger.error(
                "telegram_unexpected_error",
                error=str(e),
                symbol=position.symbol,
            )
            return None

    async def edit_position_message(
        self,
        chat_id: str,
        message_id: int,
        position: Position,
        remove_button: bool = True,
    ) -> bool:
        """Edit existing position message.

        Args:
            chat_id: Telegram chat ID
            message_id: Message ID to edit
            position: Updated position
            remove_button: Whether to remove the inline button (unused, kept for compatibility)

        Returns:
            True if successful, False otherwise
        """
        try:
            message_text = position.to_telegram_message()

            payload: dict = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": message_text,
                "parse_mode": "HTML",
            }

            response = await self.client.post(f"{self.base_url}/editMessageText", json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                logger.info(
                    "telegram_message_edited",
                    symbol=position.symbol,
                    message_id=message_id,
                )
                return True
            else:
                logger.error(
                    "telegram_edit_error",
                    error=result.get("description"),
                    symbol=position.symbol,
                )
                return False

        except httpx.HTTPError as e:
            logger.error(
                "telegram_edit_http_error",
                error=str(e),
                symbol=position.symbol,
            )
            return False
        except Exception as e:
            logger.error(
                "telegram_edit_unexpected_error",
                error=str(e),
                symbol=position.symbol,
            )
            return False

    async def answer_callback_query(
        self, callback_query_id: str, text: str = "Position closed"
    ) -> bool:
        """Answer callback query (show popup notification).

        Args:
            callback_query_id: Callback query ID
            text: Notification text

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
            }

            response = await self.client.post(
                f"{self.base_url}/answerCallbackQuery", json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result.get("ok", False)

        except Exception as e:
            logger.error("callback_answer_error", error=str(e))
            return False
