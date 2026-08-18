"""
Authentication Request Models

Pydantic models for authentication-related API requests.
"""

import re

from pydantic import Field, field_validator

from ..base import APIRequestModel


class JWTAuthHeaders(APIRequestModel):
    """
    Headers for JWT token creation endpoint.

    Endpoint: POST /auth/token

    Validates:
    - phone_number: Must be 10 digits

    Example:
        headers = JWTAuthHeaders(user_id="1001", phone_number="5550000001")
        headers_dict = headers.to_headers()
        # → {"userId": "1001", "phoneNumber": "5550000001"}
    """
    user_id: str = Field(
        ...,
        alias="userId",
        description="User ID for authentication"
    )
    phone_number: str = Field(
        ...,
        alias="phoneNumber",
        description="10-digit phone number"
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """
        Validate phone number is 10 digits.

        Removes non-numeric characters and validates length.

        Args:
            v: Phone number string

        Returns:
            Cleaned phone number (digits only)

        Raises:
            ValueError: If phone number is not 10 digits

        Example:
            "5550000001" → "5550000001" ✓
            "555-000-0001" → "5550000001" ✓
            "123" → ValueError ✗
        """
        # Remove non-numeric characters
        clean = re.sub(r'[^0-9]', '', v)

        # Validate length
        if len(clean) != 10:
            raise ValueError(
                f"Phone number must be exactly 10 digits, got {len(clean)} digits"
            )

        return clean


class RefreshTokenRequest(APIRequestModel):
    """
    Request body for JWT token refresh endpoint.

    Endpoint: POST /auth/refreshToken

    Example:
        request = RefreshTokenRequest(
            user_id="1001",
            refresh_token="abc123xyz"
        )
        body = request.to_dict()
    """
    user_id: str = Field(
        ...,
        alias="userId",
        description="User ID"
    )
    refresh_token: str = Field(
        ...,
        alias="refreshToken",
        description="Refresh token from previous authentication"
    )


class JWTAuthPartialHeaders(APIRequestModel):
    """
    Partial headers for JWT authentication (for negative testing).

    Allows missing fields to test validation errors.

    Example:
        # Missing userId (negative test)
        headers = JWTAuthPartialHeaders(phone_number="5550000001")

        # Missing phoneNumber (negative test)
        headers = JWTAuthPartialHeaders(user_id="1001")

        # Both missing (negative test)
        headers = JWTAuthPartialHeaders()
    """
    user_id: str | None = Field(
        None,
        alias="userId",
        description="User ID (optional for negative tests)"
    )
    phone_number: str | None = Field(
        None,
        alias="phoneNumber",
        description="Phone number (optional for negative tests)"
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        """Validate phone number if provided."""
        if v is None:
            return v

        # Remove non-numeric characters
        clean = re.sub(r'[^0-9]', '', v)

        # Validate length
        if len(clean) != 10:
            raise ValueError(
                f"Phone number must be exactly 10 digits, got {len(clean)} digits"
            )

        return clean
