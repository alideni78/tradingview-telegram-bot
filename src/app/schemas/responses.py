"""API response schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WebhookResponse(BaseModel):
    """Generic webhook response."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Position opened successfully",
                "data": {"symbol": "BTCUSDT", "side": "Long"},
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error detail")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {"error": "SignalParseError", "detail": "Invalid signal format"}
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    open_positions: int = Field(..., description="Number of open positions")

    class Config:
        """Pydantic config."""

        json_schema_extra = {"example": {"status": "healthy", "version": "1.0.0", "open_positions": 3}}
