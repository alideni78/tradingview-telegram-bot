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
)
@limiter.limit(lambda: get_rate_limit_string(get_settings(), "tradingview"))
async def tradingview_webhook(
    request: Request,
    webhook: TradingViewWebhook,
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    """Handle TradingView webhook alerts."""
    from ...main import position_manager, telegram_service

    logger.info("tradingview_webhook_received", message_preview=webhook.message[:100])

    try:
        signal = SignalParser.parse(webhook.message)
        logger.info(
            "signal_parsed_successfully",
            symbol=signal.symbol,
            signal_type=signal.signal_type.value,
        )
        
        # Log webhook for dashboard
        from .dashboard import log_webhook
        log_webhook(signal.symbol, signal.signal_type.value)

        if signal.is_open_signal:
            return await _handle_open_signal(signal, position_manager, telegram_service, settings)
        elif signal.is_stop_loss:
            return await _handle_stop_loss_signal(signal, position_manager, telegram_service)
        else:
            raise SignalParseError("Unknown signal type")

    except SignalParseError as e:
        logger.error("signal_parse_error", error=str(e))
        from .dashboard import log_error
        log_error(f"Parse error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid signal format: {str(e)}")
    except TelegramAPIError as e:
        logger.error("telegram_api_error", error=str(e))
        from .dashboard import log_error
        log_error(f"Telegram error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Telegram API error: {str(e)}")
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        from .dashboard import log_error
        log_error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def _handle_open_signal(signal, position_manager, telegram_service, settings):
    """Handle open signal (BUY or SELL)."""
    reply_to_message_id = None
    
    if position_manager.has_open_position(signal.symbol):
        open_position = position_manager.get_open_position(signal.symbol)
        if open_position and open_position.side == signal.position_side:
            marked_position = position_manager.mark_position_as_new(signal.symbol, signal.position_side)
            if marked_position:
                await telegram_service.edit_position_message(marked_position.chat_id, marked_position.message_id, marked_position, True)
                reply_to_message_id = marked_position.message_id
                logger.info("old_position_marked_as_new", symbol=signal.symbol)
        else:
            old_position = position_manager.handle_reverse_signal(signal.symbol)
            await telegram_service.edit_position_message(old_position.chat_id, old_position.message_id, old_position, True)
            logger.info("old_position_closed_by_reverse", symbol=signal.symbol)

    new_position = Position(
        symbol=signal.symbol,
        side=signal.position_side,
        entry_price=signal.price,
        stop_loss=signal.stop_loss,
        entry_time=signal.time,
        chat_id=settings.telegram_chat_id,
        message_id=0
    )
    
    message_id = await telegram_service.send_position_message(new_position, reply_to_message_id)
    if message_id:
        new_position.message_id = message_id
        position_manager.add_position(new_position)
        logger.info("new_position_opened", symbol=signal.symbol, message_id=message_id)
        return WebhookResponse(
            success=True,
            message="Position opened successfully",
            data={
                "symbol": signal.symbol,
                "side": signal.position_side.value if signal.position_side else None,
                "entry_price": float(signal.price)
            }
        )
    else:
        raise TelegramAPIError("Failed to send Telegram message")


async def _handle_stop_loss_signal(signal, position_manager, telegram_service):
    """Handle stop loss signal."""
    try:
        position = position_manager.handle_stop_loss(signal.symbol, signal.price)
        success = await telegram_service.edit_position_message(position.chat_id, position.message_id, position, True)
        if success:
            logger.info("position_closed_by_stop_loss", symbol=signal.symbol)
            return WebhookResponse(
                success=True,
                message="Position closed by stop loss",
                data={"symbol": signal.symbol, "exit_price": float(signal.price)}
            )
        else:
            raise TelegramAPIError("Failed to edit Telegram message")
    except PositionNotFoundError:
        logger.warning("stop_loss_for_nonexistent_position", symbol=signal.symbol)
        return WebhookResponse(
            success=False,
            message=f"No open position found for {signal.symbol}",
            data={"symbol": signal.symbol}
        )
