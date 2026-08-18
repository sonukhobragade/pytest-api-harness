"""
API Models Package

Pydantic models for API requests and responses.
Provides type-safe, validated models for all API endpoints.

Usage:
    from api_core.models.requests.auth import JWTAuthHeaders
    from api_core.models.responses.auth import JWTTokenResponse

    # Create request
    headers = JWTAuthHeaders(user_id="1001", phone_number="5550000001")

    # Parse response
    response = JWTTokenResponse.from_response(http_response)
    token = response.get_token()
"""

from .base import APIRequestModel, APIResponseModel

__all__ = [
    "APIRequestModel",
    "APIResponseModel",
]
