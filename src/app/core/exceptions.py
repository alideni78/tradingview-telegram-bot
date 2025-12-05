"""Custom exceptions."""


class ApplicationError(Exception):
    """Base application error."""

    pass


class SignalParseError(ApplicationError):
    """Error parsing TradingView signal."""

    pass


class PositionNotFoundError(ApplicationError):
    """Position not found error."""

    pass


class TelegramAPIError(ApplicationError):
    """Telegram API error."""

    pass


class WebhookAuthenticationError(ApplicationError):
    """Webhook authentication error."""

    pass
