"""Health check endpoints."""

from fastapi import APIRouter, Depends

from ...core.config import Settings, get_settings
from ...schemas import HealthResponse
from ...services import PositionManager

router = APIRouter()


@router.get("/", response_model=dict)
async def root() -> dict:
    """Root endpoint with API info.

    Returns:
        API information
    """
    return {
        "name": "TradingView to Telegram Bot",
        "version": "1.0.0",
        "description": "Production-ready trading signal notification system",
        "endpoints": {
            "tradingview_webhook": "/webhook/tradingview",
            "health": "/health",
            "docs": "/docs",
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Health check endpoint.

    Args:
        settings: Application settings

    Returns:
        Health status
    """
    from ...main import position_manager

    open_positions = len(position_manager.get_all_positions())

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        open_positions=open_positions,
    )
