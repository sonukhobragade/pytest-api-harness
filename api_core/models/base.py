"""
Base Models for API Requests and Responses

Provides base classes that all API models inherit from:
- APIRequestModel: For request bodies and headers
- APIResponseModel: For response parsing

These models provide:
- Type safety and validation
- Automatic conversion between models and dicts
- httpx integration
- Field aliasing (snake_case ↔ camelCase)
"""

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict

# Type variables for generic methods
T = TypeVar('T', bound='APIResponseModel')


class APIRequestModel(BaseModel):
    """
    Base class for all API request models (headers and bodies).

    Features:
    - Converts to dict for httpx JSON bodies
    - Converts to headers dict (string values)
    - Field aliasing (Python snake_case ↔ JSON camelCase)
    - Excludes None values by default
    - Validates data on creation and assignment

    Example:
        class JWTAuthHeaders(APIRequestModel):
            user_id: str = Field(..., alias="userId")
            phone_number: str = Field(..., alias="phoneNumber")

        # Create instance
        headers = JWTAuthHeaders(user_id="1001", phone_number="5550000001")

        # Convert to dict for httpx
        headers_dict = headers.to_headers()
        # → {"userId": "1001", "phoneNumber": "5550000001"}
    """

    model_config = ConfigDict(
        populate_by_name=True,      # Allow both field name and alias
        use_enum_values=True,       # Serialize enums as their values
        validate_assignment=True,   # Validate on field assignment
        str_strip_whitespace=True,  # Strip whitespace from strings
    )

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """
        Convert model to dictionary for httpx JSON body.

        Args:
            exclude_none: If True, exclude fields with None values (default)

        Returns:
            Dictionary with JSON field names (camelCase aliases)

        Example:
            request = CreateOrderRequest(...)
            body_dict = request.to_dict()
            await client.post(url, json=body_dict)
        """
        return self.model_dump(
            by_alias=True,          # Use JSON field names (aliases)
            exclude_none=exclude_none,  # Don't send None values
            mode='json'             # JSON-serializable types
        )

    def to_headers(self) -> dict[str, str]:
        """
        Convert model to headers dictionary (all values as strings).

        Returns:
            Dictionary with header names and string values

        Example:
            headers_model = JWTAuthHeaders(user_id="1001", phone_number="5550000001")
            headers = headers_model.to_headers()
            await client.post(url, headers=headers)
        """
        data = self.to_dict()
        # Convert all values to strings for headers
        return {k: str(v) for k, v in data.items()}


class APIResponseModel(BaseModel):
    """
    Base class for all API response models.

    Features:
    - Parse httpx.Response directly
    - Parse dict to model
    - Field aliasing (JSON camelCase ↔ Python snake_case)
    - Allows extra fields (API evolution)
    - Type-safe access to response data

    Example:
        class JWTTokenResponse(APIResponseModel):
            jwt_token: str = Field(..., alias="jwtToken")

            def get_token(self) -> str:
                return self.jwt_token

        # Parse response
        response = JWTTokenResponse.from_response(http_response)
        token = response.get_token()
    """

    model_config = ConfigDict(
        populate_by_name=True,      # Allow both field name and alias
        extra="allow",              # Allow extra fields (API changes)
        use_enum_values=True,       # Serialize enums as their values
    )

    @classmethod
    def from_response(cls: type[T], response: httpx.Response) -> T:
        """
        Parse httpx.Response into model instance.

        Args:
            response: httpx.Response object

        Returns:
            Model instance with parsed data

        Raises:
            ValidationError: If response doesn't match model schema
            JSONDecodeError: If response is not valid JSON

        Example:
            http_response = await client.post(...)
            model = JWTTokenResponse.from_response(http_response)
            token = model.jwt_token
        """
        return cls.model_validate(response.json())

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """
        Parse dictionary into model instance.

        Args:
            data: Dictionary with response data

        Returns:
            Model instance with parsed data

        Raises:
            ValidationError: If data doesn't match model schema

        Example:
            data = {"jwtToken": "abc123", "userId": "1001"}
            model = JWTTokenResponse.from_dict(data)
            token = model.jwt_token
        """
        return cls.model_validate(data)

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """
        Convert model back to dictionary.

        Args:
            exclude_none: If True, exclude fields with None values

        Returns:
            Dictionary with JSON field names (camelCase aliases)

        Example:
            response_model = JWTTokenResponse(...)
            data = response_model.to_dict()
        """
        return self.model_dump(
            by_alias=True,
            exclude_none=exclude_none,
            mode='json'
        )
