"""
Test Validator - Smart Validation Based on CSV Data

Automatically selects validation strategy based on test_data fields:
- test_type: positive/negative/edge
- expected_status: 200, 400, 401, etc.
- validation_rules: Custom validation rules from CSV (optional)

This eliminates hardcoded if/else validation in test code.
"""

from typing import Any

import allure
import httpx


class TestValidator:
    """
    Smart validator that applies appropriate validation based on test data.

    Usage:
        validator = TestValidator(test_base_instance)
        validator.validate(response, test_data)
    """

    def __init__(self, test_base):
        """
        Initialize validator with test base instance.

        Args:
            test_base: Instance of APITestBase (or subclass)
        """
        self.test_base = test_base

    def validate(self, response: httpx.Response, test_data: dict[str, Any]) -> Any:
        """
        Apply appropriate validation based on test_data.

        Automatically selects validation strategy based on:
        - expected_status: HTTP status code
        - type: positive/negative/edge/security
        - Custom validation rules (optional)

        Args:
            response: HTTP response object
            test_data: CSV row data

        Returns:
            Validation result (e.g., token, error message, etc.)

        Example:
            validator = TestValidator(self)
            result = validator.validate(response, test_data)
        """
        expected_status = test_data.get("expected_status")
        test_type = test_data.get("type", "").lower()

        with allure.step(f"Validating response for test type: {test_type}"):
            # 1. ALWAYS validate status code first
            if expected_status:
                self.test_base.assert_response_code_in(response, [expected_status])
                allure.attach(
                    f"✅ Status code validated: {response.status_code} == {expected_status}",
                    name="Status Validation",
                    attachment_type=allure.attachment_type.TEXT
                )

            # 2. Apply type-specific validation
            if test_type == "positive":
                return self._validate_positive(response, test_data)
            elif test_type == "negative":
                return self._validate_negative(response, test_data)
            elif test_type == "edge":
                return self._validate_edge_case(response, test_data)
            elif test_type == "security":
                return self._validate_security(response, test_data)
            else:
                # Default: just validate status code
                allure.attach(
                    f"⚠️ Unknown test type: {test_type}. Only status code validated.",
                    name="Validation Warning",
                    attachment_type=allure.attachment_type.TEXT
                )
                return None

    def _validate_positive(self, response: httpx.Response, test_data: dict[str, Any]) -> Any:
        """
        Validate positive test cases.

        ⭐ DELEGATES to test_base subclass for domain-specific validation.

        The test_base subclass should implement:
        - validate_positive_response(response, test_data)

        If not implemented, does basic validation.
        """
        with allure.step("✅ Positive Test Validation"):
            data = self.test_base.parse_json_safe(response)
            assert data is not None, "Positive test should return data"

            # ⭐ DELEGATE to subclass if method exists
            if hasattr(self.test_base, 'validate_positive_response'):
                return self.test_base.validate_positive_response(response, test_data)

            # Fallback: Basic validation
            allure.attach(
                "✅ Positive test passed: Valid response received",
                name="Generic Positive Validation",
                attachment_type=allure.attachment_type.TEXT
            )
            return data

    def _validate_negative(self, response: httpx.Response, test_data: dict[str, Any]) -> str:
        """
        Validate negative test cases.

        ⭐ DELEGATES to test_base subclass for domain-specific validation.

        The test_base subclass should implement:
        - validate_negative_response(response, test_data)

        If not implemented, does basic error validation.
        """
        with allure.step("❌ Negative Test Validation"):
            # ⭐ DELEGATE to subclass if method exists
            if hasattr(self.test_base, 'validate_negative_response'):
                return self.test_base.validate_negative_response(response, test_data)

            # Fallback: Basic error validation
            data = self.test_base.parse_json_safe(response)
            has_error = "error" in data or "message" in data or "msg" in data
            assert has_error, f"Negative test should return error message. Got: {list(data.keys())}"

            error_msg = data.get("error") or data.get("message") or data.get("msg")
            allure.attach(
                f"✅ Error message found: {error_msg}",
                name="Negative Test Validation",
                attachment_type=allure.attachment_type.TEXT
            )
            return error_msg

    def _validate_edge_case(self, response: httpx.Response, test_data: dict[str, Any]) -> Any:
        """
        Validate edge case tests.

        Edge cases can have either:
        - Success (200) with valid data
        - Error (4xx) with error message
        """
        with allure.step("🔶 Edge Case Validation"):
            expected_status = test_data.get("expected_status")

            if expected_status in [200, 201]:
                # Edge case that should succeed
                return self._validate_positive(response, test_data)
            else:
                # Edge case that should fail
                return self._validate_negative(response, test_data)

    def _validate_security(self, response: httpx.Response, test_data: dict[str, Any]) -> None:
        """
        Validate security test cases.

        Security tests should:
        - Return 401/403 for unauthorized access
        - NOT leak sensitive information
        - Have proper error messages
        """
        with allure.step("🔒 Security Test Validation"):
            expected_status = test_data.get("expected_status")
            data = self.test_base.parse_json_safe(response)

            # Security tests should deny access
            assert expected_status in [401, 403], \
                f"Security test should return 401/403, got {expected_status}"

            # Should have error message
            has_error = "error" in data or "message" in data
            assert has_error, "Security test should return error message"

            # Should NOT leak sensitive data
            sensitive_fields = ["password", "token", "secret", "key"]
            leaked_fields = [f for f in sensitive_fields if f in data]

            assert len(leaked_fields) == 0, \
                f"Security test leaking sensitive fields: {leaked_fields}"

            allure.attach(
                "✅ Security validation passed: No data leakage",
                name="Security Validation",
                attachment_type=allure.attachment_type.TEXT
            )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def auto_validate(test_base, response: httpx.Response, test_data: dict[str, Any]) -> Any:
    """
    Convenience function for one-line validation.

    Args:
        test_base: Test base instance
        response: HTTP response
        test_data: CSV row data

    Returns:
        Validation result

    Example:
        from api_core.utils.test_validator import auto_validate

        result = auto_validate(self, response, test_data)
    """
    validator = TestValidator(test_base)
    return validator.validate(response, test_data)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["TestValidator", "auto_validate"]
