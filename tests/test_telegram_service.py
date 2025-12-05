"""Tests for TelegramService."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

from src.app.core.config import Settings
from src.app.core.exceptions import TelegramAPIError
from src.app.models import Position, PositionSide
from src.app.services import TelegramService


class TestTelegramService:
    """Test TelegramService."""

    @pytest.mark.asyncio
    async def test_send_position_message_success(self, test_settings: Settings, sample_position: Position) -> None:
        """Test sending position message successfully."""
        telegram = TelegramService(test_settings)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 456}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(telegram.client, 'post', new_callable=AsyncMock, return_value=mock_response):
            message_id = await telegram.send_position_message(sample_position)
        
        assert message_id == 456
        await telegram.close()

    @pytest.mark.asyncio
    async def test_send_position_message_no_button(self, test_settings: Settings, sample_position: Position) -> None:
        """Test that sent message has no inline button (read-only channel)."""
        telegram = TelegramService(test_settings)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 456}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(telegram.client, 'post', new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await telegram.send_position_message(sample_position)
            
            # Check that no inline keyboard was sent
            call_args = mock_post.call_args
            payload = call_args.kwargs['json']
            assert 'reply_markup' not in payload or payload.get('reply_markup') is None
        
        await telegram.close()

    @pytest.mark.asyncio
    async def test_send_position_message_telegram_error(self, test_settings: Settings, sample_position: Position) -> None:
        """Test handling Telegram API error."""
        telegram = TelegramService(test_settings)
        
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: chat not found"
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(telegram.client, 'post', new_callable=AsyncMock, return_value=mock_response):
            message_id = await telegram.send_position_message(sample_position)
        
        assert message_id is None
        await telegram.close()

    @pytest.mark.asyncio
    async def test_edit_position_message_success(self, test_settings: Settings, sample_position: Position) -> None:
        """Test editing position message successfully."""
        telegram = TelegramService(test_settings)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        
        with patch.object(telegram.client, 'post', new_callable=AsyncMock, return_value=mock_response):
            success = await telegram.edit_position_message(
                chat_id=sample_position.chat_id,
                message_id=sample_position.message_id,
                position=sample_position,
                remove_button=True,
            )
        
        assert success is True
        await telegram.close()

    @pytest.mark.asyncio
    async def test_edit_position_message_removes_button(self, test_settings: Settings, sample_position: Position) -> None:
        """Test that editing message removes button when specified."""
        telegram = TelegramService(test_settings)
        
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        
        with patch.object(telegram.client, 'post', new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await telegram.edit_position_message(
                chat_id=sample_position.chat_id,
                message_id=sample_position.message_id,
                position=sample_position,
                remove_button=True,
            )
            
            # Check that no reply_markup was sent (button removed)
            call_args = mock_post.call_args
            payload = call_args.kwargs['json']
            assert 'reply_markup' not in payload
        
        await telegram.close()

    @pytest.mark.asyncio
    async def test_telegram_base_url(self, test_settings: Settings) -> None:
        """Test Telegram base URL construction."""
        telegram = TelegramService(test_settings)
        
        expected_url = f"https://api.telegram.org/bot{test_settings.telegram_bot_token}"
        assert telegram.base_url == expected_url
        
        await telegram.close()
