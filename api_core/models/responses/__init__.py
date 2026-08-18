"""
API Response Models

Pydantic models for API response parsing.
"""

from .auth import (
    JWTTokenResponse,
    RefreshTokenResponse,
)
from .common import (
    BooleanResponse,
    ErrorResponse,
    MessageResponse,
    PaginatedMetadata,
    PaginatedResponse,
)
__all__ = [
    # Auth responses
    "JWTTokenResponse",
    "RefreshTokenResponse",
    # Common responses
    "ErrorResponse",
    "BooleanResponse",
    "MessageResponse",
    "PaginatedMetadata",
    "PaginatedResponse",
]
