"""
Authentication Response Models

Pydantic models for authentication-related API responses.
"""


from pydantic import Field

from ..base import APIResponseModel


class JWTTokenResponse(APIResponseModel):
    """
    Response from JWT token creation endpoint.

    Endpoint: POST /auth/token

    Response format:
        {
            "jwtToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "id": 123,
            "userId": "1001"
        }

    Example:
        response = JWTTokenResponse.from_response(http_response)
        token = response.get_token()
        user_id = response.get_user_id()
    """
    jwt_token: str = Field(
        ...,
        alias="jwtToken",
        description="JWT authentication token"
    )
    user_id: str | None = Field(
        None,
        alias="userId",
        description="User ID (if returned)"
    )
    id: int | None = Field(
        None,
        description="Numeric ID (if returned)"
    )

    def get_token(self) -> str:
        """
        Get JWT token.

        Returns:
            JWT token string

        Example:
            response = JWTTokenResponse.from_response(http_response)
            token = response.get_token()
        """
        return self.jwt_token

    def get_user_id(self) -> str | None:
        """
        Get user ID if present in response.

        Returns:
            User ID string or None

        Example:
            response = JWTTokenResponse.from_response(http_response)
            user_id = response.get_user_id()
        """
        return self.user_id

    def is_valid_token(self) -> bool:
        """
        Check if token is present and non-empty.

        Returns:
            True if token exists and has content

        Example:
            response = JWTTokenResponse.from_response(http_response)
            if response.is_valid_token():
                print("Token is valid!")
        """
        return bool(self.jwt_token and len(self.jwt_token) > 0)


class RefreshTokenResponse(APIResponseModel):
    """
    Response from token refresh endpoint.

    Endpoint: POST /auth/refreshToken

    Response format:
        {
            "jwtToken": "new_token_here",
            "refreshToken": "new_refresh_token"
        }

    Example:
        response = RefreshTokenResponse.from_response(http_response)
        new_token = response.get_token()
        new_refresh = response.get_refresh_token()
    """
    jwt_token: str = Field(
        ...,
        alias="jwtToken",
        description="New JWT authentication token"
    )
    refresh_token: str | None = Field(
        None,
        alias="refreshToken",
        description="New refresh token (if rotated)"
    )

    def get_token(self) -> str:
        """Get new JWT token."""
        return self.jwt_token

    def get_refresh_token(self) -> str | None:
        """Get new refresh token if provided."""
        return self.refresh_token
