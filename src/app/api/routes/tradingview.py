"""TradingView webhook endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
import structlog

from ...core.config import Settings, get_settings
from ...core.exceptions import PositionNotFoundError, SignalParseError, TelegramAPIError
from ...models import Position
from ...schemas import TradingViewWebhook, WebhookResponse, ErrorResponse
from ...services import PositionManager, SignalParser, TelegramService
from ..dependencies import limiter, verify_webhook_secret, get_rate_limit_string

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/webhook/tradingview",
    response_model=WebhookResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid signal format"},
        401: {"model": ErrorResponse, "description": "Invalid webhook secret"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    # dependencies=[Depends(verify_webhook_secret)],  # Disabled for testing
)
@limiter.limit(lambda: get_rate_limit_string(get_settings(), "tradingview"))
async def tradingview_webhook(
    request: Request,
    webhook: TradingViewWebhook,
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    """Handle TradingView webhook alerts.

    This endpoint receives trading signals from TradingView and:
    1. Parses the signal (BUY/SELL/STOP LOSS)
    2. Manages positions (one per symbol)
    3. Sends/updates Telegram messages

    Args:
        request: FastAPI request
        webhook: Webhook payload from TradingView
        settings: Application settings

    Returns:
        WebhookResponse with operation result

    Raises:
        HTTPException: If signal parsing fails or Telegram API errors
    """
    from ...main import position_manager, telegram_service

    logger.info("tradingview_webhook_received", message_preview=webhook.message[:100])

    try:
        # Parse signal
        signal = SignalParser.parse(webhook.message)
        logger.info(
            "signal_parsed_successfully",
            symbol=signal.symbol,
            signal_type=signal.signal_type.value,
        )

        # Handle OPEN signal (BUY or SELL)
        if signal.is_open_signal:
            return await _handle_open_signal(
                signal, position_manager, telegram_service, settings
            )

        # Handle STOP LOSS signal
        elif signal.is_stop_loss:
            return await _handle_stop_loss_signal(
                signal, position_manager, telegram_service
            )

        else:
            raise SignalParseError("Unknown signal type")

    except SignalParseError as e:
        logger.error("signal_parse_error", error=str(e), message=webhook.message[:200])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signal format: {str(e)}",
        )
    except TelegramAPIError as e:
        logger.error("telegram_api_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telegram API error: {str(e)}",
        )
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def _handle_open_signal(
    signal,
    position_manager: PositionManager,
    telegram_service: TelegramService,
    settings: Settings,
) -> WebhookResponse:
    """Handle open signal (BUY or SELL).

    Args:
        signal: Parsed signal
        position_manager: Position manager instance
        telegram_service: Telegram service instance
        settings: Application settings

    Returns:
        WebhookResponse
    """
    # Check if there's an existing position for this symbol
    if position_manager.has_open_position(signal.symbol):
        open_position = position_manager.get_open_position(signal.symbol)
        
        # Check if signal is same direction
        if open_position and open_position.side == signal.position_side:
            # Same direction - mark old as NEW, create new OPEN
            marked_position = position_manager.mark_position_as_new(signal.symbol, signal.position_side)
            
            if marked_position:
                # Edit old message to show NEW status
                await telegram_service.edit_position_message(
                    chat_id=marked_position.chat_id,
                    message_id=marked_position.message_id,
                    position=marked_position,
                    remove_button=True,
                )
                
                logger.info(
                    "old_position_marked_as_new",
                    symbol=signal.symbol,
                    side=marked_position.side.value,
                )
        else:
            # Opposite direction - close with reverse signal
            old_position = position_manager.handle_reverse_signal(signal.symbol)
            
            # Edit old message to show it's closed
            await telegram_service.edit_position_message(
                chat_id=old_position.chat_id,
                message_id=old_position.message_id,
                position=old_position,
                remove_button=True,
            )
            
            logger.info(
                "old_position_closed_by_reverse",
                symbol=signal.symbol,
                old_side=old_position.side.value,
            )

    # Create new position
    new_position = Position(
        symbol=signal.symbol,
        side=signal.position_side,  # type: ignore
        entry_price=signal.price,
        stop_loss=signal.stop_loss,  # type: ignore
        entry_time=signal.time,
        chat_id=settings.telegram_chat_id,
        message_id=0,  # Will be set after sending
    )

    # Send new position message to Telegram
    message_id = await telegram_service.send_position_message(new_position)
    
    if message_id:
        new_position.message_id = message_id
        position_manager.add_position(new_position)
        
        logger.info(
            "new_position_opened",
            symbol=signal.symbol,
            side=signal.position_side.value if signal.position_side else None,  # type: ignore
            message_id=message_id,
        )
        
        return WebhookResponse(
            success=True,
            message="Position opened successfully",
            data={
                "symbol": signal.symbol,
                "side": signal.position_side.value if signal.position_side else None,  # type: ignore
                "entry_price": float(signal.price),
            },
        )
    else:
        raise TelegramAPIError("Failed to send Telegram message")


async def _handle_stop_loss_signal(
    signal,
    position_manager: PositionManager,
    telegram_service: TelegramService,
) -> WebhookResponse:
    """Handle stop loss signal.

    Args:
        signal: Parsed signal
        position_manager: Position manager instance
        telegram_service: Telegram service instance

    Returns:
        WebhookResponse
    """
    try:
        # Close position with stop loss status
        position = position_manager.handle_stop_loss(signal.symbol, signal.price)
        
        # Edit message to show stop loss hit
        success = await telegram_service.edit_position_message(
            chat_id=position.chat_id,
            message_id=position.message_id,
            position=position,
            remove_button=True,
        )
        
        if success:
            logger.info(
                "position_closed_by_stop_loss",
                symbol=signal.symbol,
                exit_price=float(signal.price),
            )
            
            return WebhookResponse(
                success=True,
                message="Position closed by stop loss",
                data={
                    "symbol": signal.symbol,
                    "exit_price": float(signal.price),
                },
            )
        else:
            raise TelegramAPIError("Failed to edit Telegram message")
            
    except PositionNotFoundError:
        logger.warning("stop_loss_for_nonexistent_position", symbol=signal.symbol)
        return WebhookResponse(
            success=False,
            message=f"No open position found for {signal.symbol}",
            data={"symbol": signal.symbol},
        )
