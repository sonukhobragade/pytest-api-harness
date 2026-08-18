"""
Common Response Models

Shared response structures used across multiple endpoints.
"""

from typing import Any

from pydantic import Field

from ..base import APIResponseModel


class ErrorResponse(APIResponseModel):
    """
    Standard error response from API.

    Common error format returned by the API when requests fail.

    Response format:
        {
            "error": "Error message here",
            "message": "Detailed message",
            "statusCode": 400
        }

    Example:
        response = ErrorResponse.from_response(http_response)
        print(response.get_error_message())
    """
    error: str | None = Field(
        None,
        description="Error type or short message"
    )
    message: str | None = Field(
        None,
        description="Detailed error message"
    )
    status_code: int | None = Field(
        None,
        alias="statusCode",
        description="HTTP status code"
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details"
    )

    def get_error_message(self) -> str:
        """
        Get the most relevant error message.

        Tries multiple fields in order of preference.

        Returns:
            Error message string

        Example:
            response = ErrorResponse.from_response(http_response)
            msg = response.get_error_message()
            print(f"Error: {msg}")
        """
        return self.message or self.error or "Unknown error"

    def is_client_error(self) -> bool:
        """
        Check if error is a client error (4xx).

        Returns:
            True if status code is in 400-499 range

        Example:
            if response.is_client_error():
                print("Client-side error (bad request, auth, etc.)")
        """
        if self.status_code:
            return 400 <= self.status_code < 500
        return False

    def is_server_error(self) -> bool:
        """
        Check if error is a server error (5xx).

        Returns:
            True if status code is in 500-599 range

        Example:
            if response.is_server_error():
                print("Server-side error")
        """
        if self.status_code:
            return 500 <= self.status_code < 600
        return False


class BooleanResponse(APIResponseModel):
    """
    Response that is just a boolean value.

    Some endpoints return just True or False.

    Example:
        response = BooleanResponse.from_response(http_response)
        if response.success:
            print("Operation succeeded!")
    """
    success: bool = Field(
        ...,
        description="Success flag"
    )

    @classmethod
    def from_response(cls, response):
        """
        Override to handle raw boolean responses.

        Args:
            response: httpx.Response object

        Returns:
            BooleanResponse instance

        Example:
            # API returns: true
            response = BooleanResponse.from_response(http_response)
            # response.success == True
        """
        try:
            data = response.json()

            # Handle raw boolean
            if isinstance(data, bool):
                return cls(success=data)

            # Handle object with success field
            return cls.model_validate(data)
        except Exception:
            # Fallback - assume failure
            return cls(success=False)


class MessageResponse(APIResponseModel):
    """
    Simple message response.

    Generic response with a message field.

    Response format:
        {
            "message": "Operation completed successfully"
        }

    Example:
        response = MessageResponse.from_response(http_response)
        print(response.message)
    """
    message: str = Field(
        ...,
        description="Response message"
    )

    def get_message(self) -> str:
        """Get the message."""
        return self.message


class PaginatedMetadata(APIResponseModel):
    """
    Pagination metadata.

    Common pagination information returned with list endpoints.

    Example:
        {
            "page": 1,
            "perPage": 10,
            "total": 50,
            "totalPages": 5
        }
    """
    page: int = Field(
        ...,
        description="Current page number"
    )
    per_page: int = Field(
        ...,
        alias="perPage",
        description="Items per page"
    )
    total: int = Field(
        ...,
        description="Total number of items"
    )
    total_pages: int = Field(
        ...,
        alias="totalPages",
        description="Total number of pages"
    )

    def has_next_page(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages

    def has_previous_page(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class PaginatedResponse(APIResponseModel):
    """
    Generic paginated response.

    Base class for responses with pagination.

    Example:
        class PaginatedUsers(PaginatedResponse):
            users: List[User]

        response = PaginatedUsers.from_response(http_response)
        if response.pagination.has_next_page():
            # Fetch next page
    """
    pagination: PaginatedMetadata | None = Field(
        None,
        description="Pagination metadata"
    )

    def is_paginated(self) -> bool:
        """Check if response has pagination."""
        return self.pagination is not None
