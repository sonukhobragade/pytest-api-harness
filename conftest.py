"""
conftest.py -- pytest wiring for the harness.

Deliberately thin. The harness supplies base classes, models, validators and
data providers; wiring them to your services belongs in your own conftest.
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("TEST_ENV", "qa"),
        help="Environment to run against (default: qa, or TEST_ENV).",
    )


@pytest.fixture(scope="session")
def env(request) -> str:
    """The environment name this run targets."""
    return request.config.getoption("--env")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """
    Base URL of the service under test.

    Required for tests that talk to a service. Skips rather than defaulting,
    because a default here means a suite that silently tests nothing, or tests
    the wrong thing.

    NOT named `base_url`: pytest-base-url registers an autouse `_verify_url`
    fixture that depends on a fixture of that name. Shadowing it meant this
    skip was pulled into every test in the session, so the whole suite skipped
    whenever BASE_URL was unset — including tests that never touch the network.
    """
    url = os.getenv("BASE_URL")
    if not url:
        pytest.skip("BASE_URL is not set; export it to run tests against a service.")
    return url
