"""
API Test Base Class - Generic Framework

Provides centralized HTTP methods, Allure logging, and response validation
for ALL API tests across the entire test suite.

Similar to Java BaseServiceHelper pattern - reusable across all endpoints.

Usage:
    # Option 1: Set in test class
    class TestUserAPI(APITestBase):
        base_url = "https://api.example.com"
        endpoint = "/users"

    # Option 2: Set in setup_class
    class TestOrderAPI(APITestBase):
        @classmethod
        def setup_class(cls):
            super().setup_class()
            cls.base_url = "https://api.example.com"
            cls.endpoint = "/orders"
"""

import json
from typing import TYPE_CHECKING, Any, Union

import allure
import httpx

from .step_executor import StepExecutor

if TYPE_CHECKING:
    from api_core.models.base import APIRequestModel, APIResponseModel


class APITestBase:
    """
    Generic base class for ALL API tests.

    Centralizes:
    - HTTP method calls (GET, POST, PUT, DELETE, PATCH)
    - Allure logging (request/response/assertions)
    - Response validation (status codes, JSON parsing)
    - Extensible for custom validations

    All API test classes should inherit from this base class.

    Example:
        class TestUserManagement(APITestBase):
            base_url = "https://api.example.com"
            endpoint = "/users"

            async def test_create_user(self):
                headers = {"Content-Type": "application/json"}
                body = {"name": "John", "email": "john@example.com"}
                response = await self.post(self.endpoint, headers=headers, body=body)
                self.assert_success_response(response)
    """

    # Class-level configuration - Override in subclass
    base_url: str = None
    endpoint: str = None
    timeout: float = 10.0

    def setup_method(self):
        """Initialize step executor before each test method"""
        self.step = StepExecutor()

    @classmethod
    def setup_class(cls):
        """
        Initialize test class - called once per test class.

        Override this method in subclass to set base_url and endpoint:

        Example:
            @classmethod
            def setup_class(cls):
                super().setup_class()
                cls.base_url = "https://api.example.com"
                cls.endpoint = "/your-endpoint"
        """
        pass

    # ==================== HTTP METHODS ====================

    async def get(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute GET request with automatic Allure logging.

        Args:
            endpoint: API endpoint (e.g., "/users/123")
            headers: Request headers
            params: Query parameters
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object

        Example:
            response = await self.get("/users/123", headers={"Authorization": "Bearer ..."})
        """
        with self.step.http_get(endpoint):
            self._log_request("GET", endpoint, headers=headers, params=params)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def post(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        body: str | dict | None = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute POST request with automatic Allure logging.

        Args:
            endpoint: API endpoint (e.g., "/users")
            headers: Request headers
            body: Request body (dict will be sent as JSON, str as raw content)
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object

        Example:
            response = await self.post("/users", headers=headers, body={"name": "John"})
        """
        with self.step.http_post(endpoint):
            self._log_request("POST", endpoint, headers=headers, body=body)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def put(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        body: str | dict | None = None,
        **kwargs
    ) -> httpx.Response:
        """Execute PUT request with automatic Allure logging."""
        with self.step.http_put(endpoint):
            self._log_request("PUT", endpoint, headers=headers, body=body)

            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def patch(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        body: str | dict | None = None,
        **kwargs
    ) -> httpx.Response:
        """Execute PATCH request with automatic Allure logging."""
        with self.step.http_patch(endpoint):
            self._log_request("PATCH", endpoint, headers=headers, body=body)

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def delete(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        **kwargs
    ) -> httpx.Response:
        """Execute DELETE request with automatic Allure logging."""
        with self.step.http_delete(endpoint):
            self._log_request("DELETE", endpoint, headers=headers)

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def head(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HEAD request with automatic Allure logging.

        HEAD is identical to GET except the server must not return a message body.
        Useful for:
        - Checking if a resource exists
        - Getting resource metadata (content-length, content-type, etc.)
        - Checking if resource has been modified (via headers)

        Args:
            endpoint: API endpoint (e.g., "/users/123")
            headers: Request headers
            params: Query parameters
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object (with headers only, no body)

        Example:
            # Check if resource exists
            response = await self.head("/users/123")
            assert response.status_code == 200

            # Get content-length without downloading
            response = await self.head("/files/large.pdf")
            size = response.headers.get("content-length")
        """
        with self.step.http_head(endpoint):
            self._log_request("HEAD", endpoint, headers=headers, params=params)

            async with httpx.AsyncClient() as client:
                response = await client.head(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    async def options(
        self,
        endpoint: str,
        headers: dict[str, str] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute OPTIONS request with automatic Allure logging.

        OPTIONS is used to describe communication options for the target resource.
        Useful for:
        - Discovering which HTTP methods are supported by an endpoint
        - CORS preflight requests
        - Checking server capabilities

        Args:
            endpoint: API endpoint (e.g., "/users" or "*" for entire server)
            headers: Request headers
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response object with Allow header listing supported methods

        Example:
            # Check supported methods
            response = await self.options("/users")
            allowed_methods = response.headers.get("Allow")
            assert "POST" in allowed_methods

            # CORS preflight check
            headers = {
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
            response = await self.options("/api/resource", headers=headers)
        """
        with self.step.http_options(endpoint):
            self._log_request("OPTIONS", endpoint, headers=headers)

            async with httpx.AsyncClient() as client:
                response = await client.options(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )

            self._log_response(response)
            return response

    # ==================== RESPONSE VALIDATORS ====================

    def assert_success_response(
        self,
        response: httpx.Response,
        expected_codes: list[int] = None
    ) -> None:
        """
        Validate successful response status code.

        Args:
            response: HTTP response object
            expected_codes: Expected status codes (default: [200, 201])

        Raises:
            AssertionError if status code doesn't match

        Example:
            self.assert_success_response(response)
            self.assert_success_response(response, [200, 204])
        """
        expected_codes = expected_codes or [200, 201]
        self._log_assertion(
            f"Status code in {expected_codes}",
            expected_codes,
            response.status_code
        )
        assert response.status_code in expected_codes, \
            f"Expected {expected_codes}, got {response.status_code}"

    def assert_error_response(
        self,
        response: httpx.Response,
        expected_codes: list[int] = None
    ) -> None:
        """
        Validate error response status code.

        Args:
            response: HTTP response object
            expected_codes: Expected error codes (default: [400, 401])

        Raises:
            AssertionError if status code doesn't match

        Example:
            self.assert_error_response(response)
            self.assert_error_response(response, [404, 422])
        """
        expected_codes = expected_codes or [400, 401]
        self._log_assertion(
            f"Status code in {expected_codes}",
            expected_codes,
            response.status_code
        )
        assert response.status_code in expected_codes, \
            f"Expected {expected_codes}, got {response.status_code}"

    def assert_response_code_in(
        self,
        response: httpx.Response,
        expected_codes: list[int]
    ) -> None:
        """
        Assert response code is in expected list (for flexible validation).

        Useful for edge case tests that accept multiple possible status codes.

        Args:
            response: HTTP response object
            expected_codes: List of acceptable status codes

        Raises:
            AssertionError if status code not in list

        Example:
            # Accept success, error, or server error
            self.assert_response_code_in(response, [200, 201, 400, 503, 504])
        """
        self._log_assertion(
            f"Status code in {expected_codes}",
            expected_codes,
            response.status_code
        )
        assert response.status_code in expected_codes, \
            f"Expected {expected_codes}, got {response.status_code}"

    def parse_json_safe(
        self,
        response: httpx.Response
    ) -> dict | list | str:
        """
        Parse response as JSON with fallback to text.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON (dict/list) or text string

        Example:
            data = self.parse_json_safe(response)
            user_id = data.get("id")
        """
        if response.status_code < 400:
            try:
                return response.json()
            except Exception:
                return response.text
        else:
            return response.text

    # ==================== MODEL-AWARE HTTP METHODS ====================

    async def post_with_model(
        self,
        endpoint: str,
        headers: Union[dict, 'APIRequestModel'] = None,
        body: Union[dict, 'APIRequestModel'] = None,
        response_model: type['APIResponseModel'] | None = None,
        **kwargs
    ) -> Union[httpx.Response, 'APIResponseModel']:
        """
        POST request with Pydantic model support.

        Accepts both dicts (backward compatible) and Pydantic models (new).
        Optionally parses response into Pydantic model.

        Args:
            endpoint: API endpoint (e.g., "/auth/token")
            headers: Dict or APIRequestModel instance (auto-converted)
            body: Dict or APIRequestModel instance (auto-converted)
            response_model: Optional response model class for parsing
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response OR parsed APIResponseModel instance

        Example (dict-based, backward compatible):
            response = await self.post_with_model(
                "/auth",
                headers={"userId": "1", "phoneNumber": "1234567890"}
            )

        Example (model-based, type-safe):
            from api_core.models.requests.auth import JWTAuthHeaders
            from api_core.models.responses.auth import JWTTokenResponse

            headers = JWTAuthHeaders(user_id="1", phone_number="1234567890")
            response = await self.post_with_model(
                "/auth/token",
                headers=headers,
                response_model=JWTTokenResponse
            )
            token = response.get_token()  # Type-safe!
        """
        # Import here to avoid circular dependency
        from api_core.models.base import APIRequestModel

        # Convert models to dicts if provided
        if headers is not None and isinstance(headers, APIRequestModel):
            headers = headers.to_headers()

        if body is not None and isinstance(body, APIRequestModel):
            body = body.to_dict()

        # Use existing post() method
        http_response = await self.post(endpoint, headers=headers, body=body, **kwargs)

        # Optionally parse into model
        if response_model:
            return response_model.from_response(http_response)

        return http_response

    async def get_with_model(
        self,
        endpoint: str,
        headers: Union[dict, 'APIRequestModel'] = None,
        params: dict = None,
        response_model: type['APIResponseModel'] | None = None,
        **kwargs
    ) -> Union[httpx.Response, 'APIResponseModel']:
        """
        GET request with Pydantic model support.

        Args:
            endpoint: API endpoint
            headers: Dict or APIRequestModel instance
            params: Query parameters
            response_model: Optional response model class for parsing
            **kwargs: Additional httpx parameters

        Returns:
            httpx.Response OR parsed APIResponseModel instance

        Example:
            from api_core.models.responses.common import PaginatedResponse

            response = await self.get_with_model(
                "/orders",
                headers={"userId": "1", "authToken": "abc"},
                response_model=PaginatedResponse
            )
            print(f"Found {len(response.data)} orders")
        """
        # Import here to avoid circular dependency
        from api_core.models.base import APIRequestModel

        # Convert model to dict if provided
        if headers is not None and isinstance(headers, APIRequestModel):
            headers = headers.to_headers()

        # Use existing get() method
        http_response = await self.get(endpoint, headers=headers, params=params, **kwargs)

        # Optionally parse into model
        if response_model:
            return response_model.from_response(http_response)

        return http_response

    async def put_with_model(
        self,
        endpoint: str,
        headers: Union[dict, 'APIRequestModel'] = None,
        body: Union[dict, 'APIRequestModel'] = None,
        response_model: type['APIResponseModel'] | None = None,
        **kwargs
    ) -> Union[httpx.Response, 'APIResponseModel']:
        """PUT request with Pydantic model support."""
        from api_core.models.base import APIRequestModel

        if headers is not None and isinstance(headers, APIRequestModel):
            headers = headers.to_headers()
        if body is not None and isinstance(body, APIRequestModel):
            body = body.to_dict()

        http_response = await self.put(endpoint, headers=headers, body=body, **kwargs)

        if response_model:
            return response_model.from_response(http_response)

        return http_response

    async def delete_with_model(
        self,
        endpoint: str,
        headers: Union[dict, 'APIRequestModel'] = None,
        response_model: type['APIResponseModel'] | None = None,
        **kwargs
    ) -> Union[httpx.Response, 'APIResponseModel']:
        """DELETE request with Pydantic model support."""
        from api_core.models.base import APIRequestModel

        if headers is not None and isinstance(headers, APIRequestModel):
            headers = headers.to_headers()

        http_response = await self.delete(endpoint, headers=headers, **kwargs)

        if response_model:
            return response_model.from_response(http_response)

        return http_response

    def parse_response_model(
        self,
        response: httpx.Response,
        model_class: type['APIResponseModel']
    ) -> 'APIResponseModel':
        """
        Helper: Parse httpx.Response into Pydantic model.

        Useful when you have a response from a non-model method
        and want to parse it into a model after the fact.

        Args:
            response: httpx.Response object
            model_class: Response model class to parse into

        Returns:
            Parsed model instance

        Example:
            # Get response using regular method
            response = await self.post("/auth", headers=headers)

            # Parse into model later
            from api_core.models.responses.auth import JWTTokenResponse
            model = self.parse_response_model(response, JWTTokenResponse)
            token = model.get_token()
        """
        return model_class.from_response(response)

    # ==================== END MODEL-AWARE METHODS ====================

    def assert_field_in_response(
        self,
        response: httpx.Response,
        field_name: str,
        attachment_name: str = None
    ) -> Any:
        """
        Validate response contains a specific field and return its value.

        Args:
            response: HTTP response object
            field_name: Name of the field to check
            attachment_name: Optional name for Allure attachment

        Returns:
            Field value

        Raises:
            AssertionError if field missing

        Example:
            user_id = self.assert_field_in_response(response, "user_id")
            token = self.assert_field_in_response(response, "access_token", "Auth Token")
        """
        data = self.parse_json_safe(response)

        self._log_assertion(
            f"Response contains '{field_name}' field",
            True,
            field_name in data
        )
        assert field_name in data, f"Response should contain '{field_name}' field"

        value = data[field_name]

        # Attach value to Allure report if requested
        if attachment_name:
            allure.attach(
                str(value),
                name=attachment_name,
                attachment_type=allure.attachment_type.TEXT
            )

        return value

    # ==================== LOGGING HELPERS ====================

    def _log_request(
        self,
        method: str,
        endpoint: str,
        headers: dict = None,
        body: Any = None,
        params: dict = None
    ) -> None:
        """Log API request to Allure"""
        request_data = {
            "method": method,
            "endpoint": endpoint
        }
        if headers:
            request_data["headers"] = headers
        if body:
            request_data["body"] = body
        if params:
            request_data["params"] = params

        allure.attach(
            json.dumps(request_data, indent=2),
            name="API Request",
            attachment_type=allure.attachment_type.JSON
        )

    def _log_response(self, response: httpx.Response) -> None:
        """Log API response to Allure"""
        body = self.parse_json_safe(response)
        response_data = {
            "status_code": response.status_code,
            "body": body if isinstance(body, (dict, list)) else str(body)
        }

        allure.attach(
            json.dumps(response_data, indent=2),
            name="API Response",
            attachment_type=allure.attachment_type.JSON
        )

    def _log_assertion(
        self,
        description: str,
        expected: Any,
        actual: Any
    ) -> None:
        """Log assertion to Allure"""
        # Determine if assertion passed
        if isinstance(expected, list):
            # For list comparisons (e.g., status code in [200, 201])
            passed = actual in expected
        else:
            # For direct comparisons
            passed = expected == actual

        assertion_data = {
            "description": description,
            "expected": expected,
            "actual": actual,
            "result": "PASS" if passed else "FAIL"
        }

        allure.attach(
            json.dumps(assertion_data, indent=2),
            name=f"Assertion: {description}",
            attachment_type=allure.attachment_type.JSON
        )
