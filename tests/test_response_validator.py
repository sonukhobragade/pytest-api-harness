"""
Tests for the fluent response validator.

The repository previously shipped no tests at all: pytest.ini pointed at a
tests/ directory that did not exist, so `pytest` collected nothing and the
harness could not be demonstrated or trusted by anyone evaluating it.

These run offline. httpx.Response is constructed directly rather than mocked,
so the assertions exercise the real object the validator receives.
"""

from __future__ import annotations

import httpx
import pytest

from api_core.utils.response_validator import validate_response


def response(payload, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=payload,
        request=httpx.Request("GET", "https://api.example.com/resource"),
    )


@pytest.fixture
def user_response():
    return response({
        "id": 42,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "score": 87,
        "tags": ["beta", "internal"],
        "nested": {"city": "London"},
    })


class TestFieldExists:
    def test_present_field_passes(self, user_response):
        validate_response(user_response).field_exists("name").assert_valid()

    def test_absent_field_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).field_exists("missing").assert_valid()

    def test_nested_field(self, user_response):
        validate_response(user_response).field_exists("nested.city").assert_valid()


class TestFieldEquals:
    def test_match_passes(self, user_response):
        validate_response(user_response).field_equals("id", 42).assert_valid()

    def test_mismatch_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).field_equals("id", 43).assert_valid()

    def test_type_matters(self, user_response):
        """42 and "42" are not the same value; a validator that treats them as
        equal will pass a response whose types have silently changed."""
        with pytest.raises(AssertionError):
            validate_response(user_response).field_equals("id", "42").assert_valid()


class TestFieldType:
    def test_correct_type_passes(self, user_response):
        validate_response(user_response).field_type("id", int).assert_valid()

    def test_wrong_type_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).field_type("id", str).assert_valid()


class TestFieldInRange:
    def test_inside_range_passes(self, user_response):
        validate_response(user_response).field_in_range("score", 0, 100).assert_valid()

    def test_outside_range_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).field_in_range("score", 0, 50).assert_valid()

    def test_boundaries_are_inclusive(self, user_response):
        validate_response(user_response).field_in_range("score", 87, 87).assert_valid()


class TestArrays:
    def test_length(self, user_response):
        validate_response(user_response).array_length("tags", 2).assert_valid()

    def test_wrong_length_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).array_length("tags", 3).assert_valid()

    def test_contains(self, user_response):
        validate_response(user_response).array_contains("tags", "beta").assert_valid()

    def test_missing_member_fails(self, user_response):
        with pytest.raises(AssertionError):
            validate_response(user_response).array_contains("tags", "alpha").assert_valid()


class TestRequiredFields:
    def test_all_present_passes(self, user_response):
        validate_response(user_response).validate_required_fields(
            ["id", "name", "email"]
        ).assert_valid()

    def test_reports_every_missing_field(self, user_response):
        """One assertion per run is a slow way to fix a broken contract; the
        failure should name all of them."""
        with pytest.raises(AssertionError) as excinfo:
            validate_response(user_response).validate_required_fields(
                ["id", "absent_one", "absent_two"]
            ).assert_valid()
        message = str(excinfo.value)
        assert "absent_one" in message and "absent_two" in message


class TestChaining:
    def test_failures_accumulate(self, user_response):
        """The validator is fluent, so a chain must collect failures rather
        than stopping at the first one."""
        with pytest.raises(AssertionError) as excinfo:
            (
                validate_response(user_response)
                .field_equals("id", 999)
                .field_exists("nope")
                .assert_valid()
            )
        assert str(excinfo.value).count("\n") >= 1

    def test_a_passing_chain_raises_nothing(self, user_response):
        (
            validate_response(user_response)
            .field_exists("id")
            .field_type("name", str)
            .field_not_empty("email")
            .array_length("tags", 2)
            .assert_valid()
        )
