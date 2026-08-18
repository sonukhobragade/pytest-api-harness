"""
Logging utilities for test framework.

Provides functions for logging API requests, responses, and assertions to Allure reports.
"""
import json

import allure


def log_api_request(method: str, endpoint: str, headers: dict = None, body=None):
    """
    Log API request details to Allure report.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        headers: Request headers dict
        body: Request body (dict or string)
    """
    request_data = {
        "method": method,
        "endpoint": endpoint
    }

    if headers:
        request_data["headers"] = headers

    if body:
        request_data["body"] = body

    allure.attach(
        json.dumps(request_data, indent=2),
        name="API Request",
        attachment_type=allure.attachment_type.JSON
    )


def log_api_response(status_code: int, response_body):
    """
    Log API response details to Allure report.

    Args:
        status_code: HTTP status code
        response_body: Response body (dict, string, or any JSON-serializable)
    """
    response_data = {
        "status_code": status_code,
        "body": response_body if isinstance(response_body, (dict, list)) else str(response_body)
    }

    allure.attach(
        json.dumps(response_data, indent=2),
        name="API Response",
        attachment_type=allure.attachment_type.JSON
    )


def log_assertion(description: str, expected, actual):
    """
    Log assertion details to Allure report.

    Args:
        description: Description of what is being asserted
        expected: Expected value
        actual: Actual value
    """
    assertion_data = {
        "description": description,
        "expected": expected,
        "actual": actual,
        "result": "PASS" if expected == actual else "FAIL"
    }

    allure.attach(
        json.dumps(assertion_data, indent=2),
        name=f"Assertion: {description}",
        attachment_type=allure.attachment_type.JSON
    )
