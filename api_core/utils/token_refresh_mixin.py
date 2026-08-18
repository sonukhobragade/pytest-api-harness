"""
Token Auto-Refresh Mixin

Provides automatic token refresh on 401 Unauthorized responses.
When a request receives 401, automatically calls issueToken to get fresh token
and retries the original request.
"""

from typing import Any

import allure
import httpx


class TokenRefreshMixin:
    """
    Mixin class for automatic token refresh on 401 responses.

    Usage:
        class OrdersTestBase(APITestBase, TokenRefreshMixin):
            ...

    Features:
    - Auto-detects 401 responses
    - Calls issueToken with userId + phoneNumber
    - Updates auth_token in headers
    - Retries original request
    - Logs all steps to Allure
    """

    async def get_with_auto_refresh(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        user_id: str | None = None,
        phone_number: str | None = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute GET request with automatic token refresh on 401.

        Args:
            endpoint: API endpoint
            headers: Request headers (should contain auth_token)
            user_id: User ID for token refresh (required if 401 occurs)
            phone_number: Phone number for token refresh (required if 401 occurs)
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object

        Example:
            response = await self.get_with_auto_refresh(
                "/orders",
                headers={"userId": "1", "auth_token": "..."},
                user_id="1",
                phone_number="5550000001"
            )
        """
        response = await self.get(endpoint, headers=headers, **kwargs)

        # Auto-refresh on 401
        if response.status_code == 401:
            response = await self._handle_401_and_retry(
                "GET", endpoint, headers, user_id, phone_number, **kwargs
            )

        return response

    async def post_with_auto_refresh(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        body: Any = None,
        user_id: str | None = None,
        phone_number: str | None = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute POST request with automatic token refresh on 401.

        Args:
            endpoint: API endpoint
            headers: Request headers
            body: Request body
            user_id: User ID for token refresh
            phone_number: Phone number for token refresh
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object
        """
        response = await self.post(endpoint, headers=headers, body=body, **kwargs)

        # Auto-refresh on 401
        if response.status_code == 401:
            response = await self._handle_401_and_retry(
                "POST", endpoint, headers, user_id, phone_number, body=body, **kwargs
            )

        return response

    async def delete_with_auto_refresh(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        user_id: str | None = None,
        phone_number: str | None = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute DELETE request with automatic token refresh on 401.

        Args:
            endpoint: API endpoint
            headers: Request headers
            user_id: User ID for token refresh
            phone_number: Phone number for token refresh
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object

        Example:
            response = await self.delete_with_auto_refresh(
                "/orders/42",
                headers={"userId": "1", "auth_token": "..."},
                user_id="1",
                phone_number="5550000001"
            )
        """
        response = await self.delete(endpoint, headers=headers, **kwargs)

        # Auto-refresh on 401
        if response.status_code == 401:
            response = await self._handle_401_and_retry(
                "DELETE", endpoint, headers, user_id, phone_number, **kwargs
            )

        return response

    async def _handle_401_and_retry(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str],
        user_id: str | None,
        phone_number: str | None,
        **kwargs
    ) -> httpx.Response:
        """
        Handle 401 response by refreshing token and retrying request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            headers: Original request headers
            user_id: User ID for token refresh
            phone_number: Phone number for token refresh
            **kwargs: Additional request parameters

        Returns:
            Retried response with fresh token

        Raises:
            ValueError: If user_id or phone_number not provided
        """
        with allure.step("🔄 Auto-Refresh Token on 401 Unauthorized"):
            allure.attach(
                "Received 401 Unauthorized - Auto-refreshing token",
                name="Token Refresh Triggered",
                attachment_type=allure.attachment_type.TEXT
            )

            # Validate required parameters
            if not user_id or not phone_number:
                error_msg = (
                    "Cannot auto-refresh token: user_id and phone_number required.\n"
                    f"Provided: user_id={user_id}, phone_number={phone_number}"
                )
                allure.attach(error_msg, name="❌ Refresh Failed", attachment_type=allure.attachment_type.TEXT)
                raise ValueError(error_msg)

            # Call issueToken to get fresh token
            fresh_token = await self._refresh_jwt_token(user_id, phone_number)

            # Update headers with fresh token
            if headers is None:
                headers = {}
            headers["auth_token"] = fresh_token

            allure.attach(
                "Fresh token obtained and updated in headers",
                name="✅ Token Refreshed",
                attachment_type=allure.attachment_type.TEXT
            )

            # Retry original request with fresh token
            with allure.step(f"Retrying {method} request with fresh token"):
                if method == "GET":
                    response = await self.get(endpoint, headers=headers, **kwargs)
                elif method == "POST":
                    response = await self.post(endpoint, headers=headers, **kwargs)
                elif method == "PUT":
                    response = await self.put(endpoint, headers=headers, **kwargs)
                elif method == "PATCH":
                    response = await self.patch(endpoint, headers=headers, **kwargs)
                elif method == "DELETE":
                    response = await self.delete(endpoint, headers=headers, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                return response

    async def _refresh_jwt_token(self, user_id: str, phone_number: str) -> str:
        """
        Call issueToken endpoint to get fresh token.

        Args:
            user_id: User ID
            phone_number: Phone number

        Returns:
            Fresh JWT token string

        Raises:
            AssertionError: If token creation fails
        """
        with allure.step(f"Calling issueToken for user {user_id}"):
            from tests.config.endpoints import AUTH_CREATE_JWT, BASE_URL

            # Build request
            jwt_headers = {
                "userId": user_id,
                "phoneNumber": phone_number
            }

            # Call issueToken endpoint
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{BASE_URL}{AUTH_CREATE_JWT}",
                    headers=jwt_headers
                )

            # Validate response
            assert response.status_code in [200, 201], \
                f"Token refresh failed: {response.status_code} - {response.text}"

            # Extract token
            data = response.json()
            assert "jwtToken" in data, "Token refresh response missing 'jwtToken' field"

            token = data["jwtToken"]
            assert len(token) > 0, "Token refresh returned empty token"

            allure.attach(
                f"User: {user_id}\nToken: {token[:20]}...",
                name="Fresh JWT Token",
                attachment_type=allure.attachment_type.TEXT
            )

            return token


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["TokenRefreshMixin"]
