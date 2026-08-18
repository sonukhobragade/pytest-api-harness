"""
Step Executor - Generic Allure Step Management

Centralizes all allure.step() usage across the framework.
Provides reusable step execution methods for tests.

Benefits:
- Single source of truth for step logging
- Consistent step naming across all tests
- Easy to customize step behavior globally
- Reduces boilerplate in test code
"""

from contextlib import contextmanager

import allure


class StepExecutor:
    """
    Generic step executor for Allure reporting.

    Provides methods for executing code within named Allure steps,
    with automatic logging and error handling.

    Usage:
        # In test base class
        class APITestBase:
            def __init__(self):
                self.step = StepExecutor()

        # In tests
        async def test_example(self):
            with self.step.http_request("POST", "/users"):
                # HTTP call code
                pass

            with self.step.custom("Validate user created"):
                # Validation code
                pass
    """

    # ==================== HTTP STEP METHODS ====================

    @contextmanager
    def http_request(self, method: str, endpoint: str):
        """
        Execute HTTP request step.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint

        Example:
            with self.step.http_request("POST", "/users"):
                response = await client.post(...)
        """
        with allure.step(f"Send {method} request to {endpoint}"):
            yield

    @contextmanager
    def http_get(self, endpoint: str):
        """Shorthand for GET requests"""
        with allure.step(f"Send GET request to {endpoint}"):
            yield

    @contextmanager
    def http_post(self, endpoint: str):
        """Shorthand for POST requests"""
        with allure.step(f"Send POST request to {endpoint}"):
            yield

    @contextmanager
    def http_put(self, endpoint: str):
        """Shorthand for PUT requests"""
        with allure.step(f"Send PUT request to {endpoint}"):
            yield

    @contextmanager
    def http_patch(self, endpoint: str):
        """Shorthand for PATCH requests"""
        with allure.step(f"Send PATCH request to {endpoint}"):
            yield

    @contextmanager
    def http_delete(self, endpoint: str):
        """Shorthand for DELETE requests"""
        with allure.step(f"Send DELETE request to {endpoint}"):
            yield

    @contextmanager
    def http_head(self, endpoint: str):
        """Shorthand for HEAD requests"""
        with allure.step(f"Send HEAD request to {endpoint}"):
            yield

    @contextmanager
    def http_options(self, endpoint: str):
        """Shorthand for OPTIONS requests"""
        with allure.step(f"Send OPTIONS request to {endpoint}"):
            yield

    # ==================== VALIDATION STEP METHODS ====================

    @contextmanager
    def validate_response(self, description: str = "Validate response"):
        """
        Execute response validation step.

        Args:
            description: Custom description for the validation step

        Example:
            with self.step.validate_response("Verify user created"):
                assert response.status_code == 201
        """
        with allure.step(description):
            yield

    @contextmanager
    def validate_status_code(self, expected_codes):
        """
        Execute status code validation step.

        Example:
            with self.step.validate_status_code([200, 201]):
                assert response.status_code in [200, 201]
        """
        with allure.step(f"Validate status code in {expected_codes}"):
            yield

    @contextmanager
    def validate_field(self, field_name: str):
        """
        Execute field validation step.

        Example:
            with self.step.validate_field("user_id"):
                assert "user_id" in response.json()
        """
        with allure.step(f"Validate field '{field_name}' exists"):
            yield

    # ==================== DATA PREPARATION STEP METHODS ====================

    @contextmanager
    def prepare_data(self, description: str = "Prepare test data"):
        """
        Execute data preparation step.

        Example:
            with self.step.prepare_data("Build request headers"):
                headers = {"Authorization": "Bearer token"}
        """
        with allure.step(description):
            yield

    @contextmanager
    def build_request(self, description: str = "Build request"):
        """Execute request building step"""
        with allure.step(description):
            yield

    @contextmanager
    def build_headers(self, description: str = "Build request headers"):
        """Execute header building step"""
        with allure.step(description):
            yield

    @contextmanager
    def build_payload(self, description: str = "Build request payload"):
        """Execute payload building step"""
        with allure.step(description):
            yield

    # ==================== GENERIC STEP METHODS ====================

    @contextmanager
    def custom(self, description: str):
        """
        Execute custom named step.

        Args:
            description: Step description

        Example:
            with self.step.custom("Extract user ID from response"):
                user_id = response.json()["user_id"]
        """
        with allure.step(description):
            yield

    @contextmanager
    def action(self, action_name: str, target: str | None = None):
        """
        Execute generic action step.

        Args:
            action_name: Action being performed (Create, Update, Delete, etc.)
            target: Optional target of the action

        Example:
            with self.step.action("Create", "user"):
                # Creation logic
                pass

            with self.step.action("Verify", "token generated"):
                # Verification logic
                pass
        """
        if target:
            description = f"{action_name} {target}"
        else:
            description = action_name

        with allure.step(description):
            yield

    # ==================== ADVANCED STEP METHODS ====================

    @contextmanager
    def database_operation(self, operation: str, table: str = None):
        """
        Execute database operation step.

        Example:
            with self.step.database_operation("Query", "users"):
                result = db.query("SELECT * FROM users")
        """
        if table:
            description = f"Database: {operation} on '{table}' table"
        else:
            description = f"Database: {operation}"

        with allure.step(description):
            yield

    @contextmanager
    def external_service_call(self, service_name: str, operation: str = None):
        """
        Execute external service call step.

        Example:
            with self.step.external_service_call("Payment Gateway", "Process payment"):
                payment_result = payment_gateway.process(...)
        """
        if operation:
            description = f"External Service: {service_name} - {operation}"
        else:
            description = f"External Service: {service_name}"

        with allure.step(description):
            yield

    @contextmanager
    def setup_teardown(self, description: str):
        """
        Execute setup/teardown step.

        Example:
            with self.step.setup_teardown("Initialize test environment"):
                # Setup code
                pass
        """
        with allure.step(f"Setup: {description}"):
            yield

    # ==================== PARAMETERIZED STEP METHODS ====================

    @contextmanager
    def iteration(self, index: int, total: int, description: str = None):
        """
        Execute iteration step (useful for loops).

        Example:
            for i in range(3):
                with self.step.iteration(i, 3, "Request token"):
                    response = await self.post(...)
        """
        if description:
            step_desc = f"Iteration {index + 1}/{total}: {description}"
        else:
            step_desc = f"Iteration {index + 1}/{total}"

        with allure.step(step_desc):
            yield

    @contextmanager
    def retry(self, attempt: int, max_attempts: int, description: str = None):
        """
        Execute retry step.

        Example:
            for attempt in range(max_retries):
                with self.step.retry(attempt, max_retries, "Connect to API"):
                    try:
                        response = await self.get(...)
                        break
                    except:
                        continue
        """
        if description:
            step_desc = f"Retry {attempt + 1}/{max_attempts}: {description}"
        else:
            step_desc = f"Retry attempt {attempt + 1}/{max_attempts}"

        with allure.step(step_desc):
            yield

    # ==================== CONDITIONAL STEP METHODS ====================

    @contextmanager
    def conditional(self, condition_name: str, condition_value: bool):
        """
        Execute conditional step with condition result in description.

        Example:
            with self.step.conditional("User exists", user_exists):
                if user_exists:
                    # Update user
                else:
                    # Create user
        """
        result = "TRUE" if condition_value else "FALSE"
        with allure.step(f"Condition: {condition_name} = {result}"):
            yield

    # ==================== MEASUREMENT STEP METHODS ====================

    @contextmanager
    def measure_time(self, operation: str):
        """
        Execute timed operation step (measurement done by caller).

        Example:
            import time
            with self.step.measure_time("API response time"):
                start = time.time()
                response = await self.post(...)
                elapsed = time.time() - start
                allure.attach(f"{elapsed:.3f}s", name="Duration")
        """
        with allure.step(f"Measure: {operation}"):
            yield

    # ==================== ATTACHMENT METHODS ====================

    def attach_text(self, content: str, name: str = "Text Data"):
        """
        Attach text content to Allure report.

        Args:
            content: Text content to attach
            name: Attachment name in report

        Example:
            self.step.attach_text(token, name="JWT Token")
            self.step.attach_text(error_msg, name="Error Message")
        """
        allure.attach(
            str(content),
            name=name,
            attachment_type=allure.attachment_type.TEXT
        )

    def attach_json(self, data: dict, name: str = "JSON Data"):
        """
        Attach JSON data to Allure report.

        Args:
            data: Dictionary to attach as JSON
            name: Attachment name in report

        Example:
            self.step.attach_json(response_data, name="Response Body")
            self.step.attach_json(request_data, name="Request Payload")
        """
        import json
        allure.attach(
            json.dumps(data, indent=2),
            name=name,
            attachment_type=allure.attachment_type.JSON
        )

    def attach_html(self, html_content: str, name: str = "HTML Content"):
        """
        Attach HTML content to Allure report.

        Args:
            html_content: HTML string to attach
            name: Attachment name in report

        Example:
            self.step.attach_html(html_response, name="API Response")
        """
        allure.attach(
            html_content,
            name=name,
            attachment_type=allure.attachment_type.HTML
        )

    def attach_xml(self, xml_content: str, name: str = "XML Data"):
        """
        Attach XML content to Allure report.

        Args:
            xml_content: XML string to attach
            name: Attachment name in report

        Example:
            self.step.attach_xml(xml_response, name="SOAP Response")
        """
        allure.attach(
            xml_content,
            name=name,
            attachment_type=allure.attachment_type.XML
        )

    def attach_csv(self, csv_content: str, name: str = "CSV Data"):
        """
        Attach CSV content to Allure report.

        Args:
            csv_content: CSV string to attach
            name: Attachment name in report

        Example:
            self.step.attach_csv(csv_data, name="Test Data")
        """
        allure.attach(
            csv_content,
            name=name,
            attachment_type=allure.attachment_type.CSV
        )

    def attach_file(self, file_path: str, name: str = None):
        """
        Attach file to Allure report.

        Args:
            file_path: Path to file to attach
            name: Optional attachment name (defaults to filename)

        Example:
            self.step.attach_file("/tmp/screenshot.png", name="Screenshot")
        """
        if name is None:
            import os
            name = os.path.basename(file_path)

        with open(file_path, 'rb') as f:
            allure.attach(
                f.read(),
                name=name,
                attachment_type=allure.attachment_type.TEXT
            )

    # ==================== DOMAIN-SPECIFIC ATTACHMENT HELPERS ====================

    def attach_token(self, token: str, token_type: str = "JWT"):
        """
        Attach authentication token to Allure report.

        Args:
            token: Token string to attach
            token_type: Type of token (JWT, OAuth, Bearer, etc.)

        Example:
            self.step.attach_token(jwt_token, token_type="JWT")
            self.step.attach_token(oauth_token, token_type="OAuth")
        """
        # Truncate long tokens for display
        display_token = token[:50] + "..." if len(token) > 50 else token

        allure.attach(
            display_token,
            name=f"{token_type} Token",
            attachment_type=allure.attachment_type.TEXT
        )

    def attach_error(self, error_message: str, error_code: str = None):
        """
        Attach error message to Allure report.

        Args:
            error_message: Error message text
            error_code: Optional error code

        Example:
            self.step.attach_error("User not found", error_code="404")
            self.step.attach_error(response.get("error"))
        """
        if error_code:
            content = f"Error Code: {error_code}\nMessage: {error_message}"
        else:
            content = error_message

        allure.attach(
            content,
            name="Error Message",
            attachment_type=allure.attachment_type.TEXT
        )

    def attach_response(self, response_data: dict, name: str = "API Response"):
        """
        Attach API response data to Allure report.

        Args:
            response_data: Response dictionary
            name: Attachment name

        Example:
            self.step.attach_response(data, name="JWT Response")
            self.step.attach_response(orders, name="Orders Response")
        """
        self.attach_json(response_data, name=name)

    def attach_request(self, request_data: dict, name: str = "API Request"):
        """
        Attach API request data to Allure report.

        Args:
            request_data: Request dictionary (headers, body, etc.)
            name: Attachment name

        Example:
            self.step.attach_request({"headers": headers, "body": body})
        """
        self.attach_json(request_data, name=name)

    def attach_validation_result(self, result: str, passed: bool = True):
        """
        Attach validation result to Allure report.

        Args:
            result: Validation result message
            passed: Whether validation passed

        Example:
            self.step.attach_validation_result("✅ Token validated", passed=True)
            self.step.attach_validation_result("❌ Missing field", passed=False)
        """
        prefix = "✅" if passed else "❌"
        allure.attach(
            f"{prefix} {result}",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )


# ==================== SINGLETON INSTANCE ====================

# Global step executor instance (optional convenience)
step = StepExecutor()


# ==================== DECORATOR FOR AUTOMATIC STEPS ====================

def auto_step(step_name: str = None):
    """
    Decorator to automatically wrap function in an Allure step.

    Args:
        step_name: Optional custom step name (defaults to function name)

    Example:
        @auto_step("Create new user")
        async def create_user(self, user_data):
            # Function becomes an Allure step automatically
            return await self.post("/users", body=user_data)

        @auto_step()  # Uses function name
        async def validate_token(self, token):
            assert len(token) > 0
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            name = step_name or func.__name__.replace('_', ' ').title()
            with allure.step(name):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            name = step_name or func.__name__.replace('_', ' ').title()
            with allure.step(name):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
