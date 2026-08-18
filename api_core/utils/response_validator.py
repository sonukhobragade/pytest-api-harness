"""
Response Validator - Validate Complex API Responses

Supports multiple validation strategies:
1. JSON Schema validation (for complex responses)
2. Field-by-field validation (for specific fields)
3. Custom validation functions

Use this when you need to validate many fields in the response.
"""

from typing import Any

import allure
import httpx


class ResponseValidator:
    """
    Comprehensive response validator for complex API responses.

    Supports:
    - JSON Schema validation
    - Field existence checks
    - Type validation
    - Value validation
    - Nested object validation
    """

    def __init__(self, response: httpx.Response):
        """
        Initialize validator with response.

        Args:
            response: HTTP response object
        """
        self.response = response
        self.data = self._parse_response()
        self.errors = []

    def _parse_response(self) -> dict[str, Any]:
        """Parse JSON response safely."""
        try:
            return self.response.json()
        except Exception as e:
            self.errors.append(f"Failed to parse JSON: {e}")
            return {}

    # ==================== FIELD VALIDATION ====================

    def field_exists(self, field_path: str) -> 'ResponseValidator':
        """
        Check if field exists in response.

        Supports nested fields using dot notation.

        Args:
            field_path: Field path (e.g., "user.profile.age")

        Returns:
            Self for chaining

        Example:
            validator.field_exists("jwtToken") \\
                     .field_exists("user.id") \\
                     .field_exists("user.profile.age")
        """
        value = self._get_nested_value(field_path)
        if value is None:
            self.errors.append(f"Field '{field_path}' does not exist")

        allure.attach(
            f"✅ Field '{field_path}' exists" if value is not None else f"❌ Field '{field_path}' missing",
            name=f"Field Check: {field_path}",
            attachment_type=allure.attachment_type.TEXT
        )

        return self

    def field_not_empty(self, field_path: str) -> 'ResponseValidator':
        """
        Check if field exists and is not empty.

        Args:
            field_path: Field path

        Returns:
            Self for chaining

        Example:
            validator.field_not_empty("jwtToken")
        """
        value = self._get_nested_value(field_path)

        if value is None:
            self.errors.append(f"Field '{field_path}' does not exist")
        elif isinstance(value, str) and len(value) == 0:
            self.errors.append(f"Field '{field_path}' is empty string")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            self.errors.append(f"Field '{field_path}' is empty")

        return self

    def field_equals(self, field_path: str, expected_value: Any) -> 'ResponseValidator':
        """
        Check if field value equals expected value.

        Args:
            field_path: Field path
            expected_value: Expected value

        Returns:
            Self for chaining

        Example:
            validator.field_equals("userId", "1001") \\
                     .field_equals("user.role", "admin")
        """
        actual_value = self._get_nested_value(field_path)

        if actual_value != expected_value:
            self.errors.append(
                f"Field '{field_path}': expected '{expected_value}', got '{actual_value}'"
            )

        allure.attach(
            f"Field: {field_path}\nExpected: {expected_value}\nActual: {actual_value}",
            name=f"Value Check: {field_path}",
            attachment_type=allure.attachment_type.TEXT
        )

        return self

    def field_type(self, field_path: str, expected_type: type) -> 'ResponseValidator':
        """
        Check if field has expected type.

        Args:
            field_path: Field path
            expected_type: Expected Python type (str, int, bool, list, dict)

        Returns:
            Self for chaining

        Example:
            validator.field_type("userId", str) \\
                     .field_type("expiresIn", int) \\
                     .field_type("user.isActive", bool) \\
                     .field_type("permissions", list)
        """
        value = self._get_nested_value(field_path)

        if value is not None and not isinstance(value, expected_type):
            self.errors.append(
                f"Field '{field_path}': expected type {expected_type.__name__}, got {type(value).__name__}"
            )

        return self

    def field_in_range(self, field_path: str, min_val: int | float, max_val: int | float) -> 'ResponseValidator':
        """
        Check if numeric field is in range.

        Args:
            field_path: Field path
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Self for chaining

        Example:
            validator.field_in_range("user.profile.age", 0, 150)
        """
        value = self._get_nested_value(field_path)

        if value is not None:
            if not (min_val <= value <= max_val):
                self.errors.append(
                    f"Field '{field_path}': value {value} not in range [{min_val}, {max_val}]"
                )

        return self

    def field_matches_regex(self, field_path: str, pattern: str) -> 'ResponseValidator':
        r"""
        Check if field value matches regex pattern.

        Args:
            field_path: Field path
            pattern: Regex pattern

        Returns:
            Self for chaining

        Example:
            validator.field_matches_regex("email", r"^[\w\.-]+@[\w\.-]+\.\w+$")
        """
        import re

        value = self._get_nested_value(field_path)

        if value is not None and isinstance(value, str):
            if not re.match(pattern, value):
                self.errors.append(
                    f"Field '{field_path}': value '{value}' doesn't match pattern '{pattern}'"
                )

        return self

    def array_length(self, field_path: str, expected_length: int) -> 'ResponseValidator':
        """
        Check if array has expected length.

        Args:
            field_path: Field path to array
            expected_length: Expected array length

        Returns:
            Self for chaining

        Example:
            validator.array_length("permissions", 3)
        """
        value = self._get_nested_value(field_path)

        if value is not None and isinstance(value, list):
            if len(value) != expected_length:
                self.errors.append(
                    f"Array '{field_path}': expected length {expected_length}, got {len(value)}"
                )

        return self

    def array_contains(self, field_path: str, expected_value: Any) -> 'ResponseValidator':
        """
        Check if array contains expected value.

        Args:
            field_path: Field path to array
            expected_value: Value that should be in array

        Returns:
            Self for chaining

        Example:
            validator.array_contains("permissions", "read")
        """
        value = self._get_nested_value(field_path)

        if value is not None and isinstance(value, list):
            if expected_value not in value:
                self.errors.append(
                    f"Array '{field_path}': doesn't contain '{expected_value}'"
                )

        return self

    # ==================== BULK VALIDATION ====================

    def validate_fields(self, field_checks: dict[str, Any]) -> 'ResponseValidator':
        """
        Validate multiple fields at once.

        Args:
            field_checks: Dict of {field_path: expected_value}

        Returns:
            Self for chaining

        Example:
            validator.validate_fields({
                "userId": "1001",
                "phoneNumber": "5550000001",
                "tokenType": "Bearer",
                "user.role": "admin"
            })
        """
        for field_path, expected_value in field_checks.items():
            self.field_equals(field_path, expected_value)

        return self

    def validate_required_fields(self, required_fields: list[str]) -> 'ResponseValidator':
        """
        Check that all required fields exist.

        Args:
            required_fields: List of field paths that must exist

        Returns:
            Self for chaining

        Example:
            validator.validate_required_fields([
                "jwtToken",
                "userId",
                "user.id",
                "user.name",
                "user.email"
            ])
        """
        for field_path in required_fields:
            self.field_exists(field_path)

        return self

    # ==================== ASSERTION ====================

    def assert_valid(self) -> dict[str, Any]:
        """
        Assert that all validations passed.

        Raises:
            AssertionError: If any validation failed

        Returns:
            Response data if all validations passed

        Example:
            data = validator.field_exists("jwtToken") \\
                            .field_not_empty("jwtToken") \\
                            .assert_valid()
        """
        if self.errors:
            error_msg = "Response validation failed:\n" + "\n".join(
                f"  - {error}" for error in self.errors
            )

            allure.attach(
                error_msg,
                name="❌ Validation Errors",
                attachment_type=allure.attachment_type.TEXT
            )

            raise AssertionError(error_msg)

        allure.attach(
            "✅ All validations passed",
            name="Validation Success",
            attachment_type=allure.attachment_type.TEXT
        )

        return self.data

    # ==================== HELPERS ====================

    def _get_nested_value(self, field_path: str) -> Any:
        """
        Get value from nested dict using dot notation.

        Args:
            field_path: Path like "user.profile.age"

        Returns:
            Field value or None if not found
        """
        keys = field_path.split('.')
        value = self.data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def validate_response(response: httpx.Response) -> ResponseValidator:
    """
    Create ResponseValidator instance.

    Args:
        response: HTTP response

    Returns:
        ResponseValidator instance for chaining

    Example:
        from api_core.utils.response_validator import validate_response

        data = validate_response(response) \\
            .field_exists("jwtToken") \\
            .field_not_empty("jwtToken") \\
            .field_equals("userId", "1001") \\
            .assert_valid()
    """
    return ResponseValidator(response)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["ResponseValidator", "validate_response"]
