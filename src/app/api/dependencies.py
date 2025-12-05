"""API dependencies for rate limiting and authentication."""

from typing import Annotated

from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.config import Settings, get_settings
from ..core.exceptions import WebhookAuthenticationError

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def verify_webhook_secret(
    x_webhook_secret: Annotated[str | None, Header()] = None,
    settings: Settings = None,
) -> None:
    """Verify webhook secret header.

    Args:
        x_webhook_secret: Webhook secret from header
        settings: Application settings

    Raises:
        HTTPException: If secret is invalid
    """
    if settings is None:
        settings = get_settings()

    if not x_webhook_secret or x_webhook_secret != settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )


def get_rate_limit_string(settings: Settings, endpoint: str) -> str:
    """Get rate limit string for endpoint.

    Args:
        settings: Application settings
        endpoint: Endpoint name (tradingview or telegram)

    Returns:
        Rate limit string (e.g., '60/minute')
    """
    if endpoint == "tradingview":
        return f"{settings.rate_limit_tradingview}/minute"
    return f"{settings.rate_limit_telegram}/minute"
