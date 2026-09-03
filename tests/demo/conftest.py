"""Fixtures for the demo-stack suite.

Everything here targets the local stack in ``demo/docker-compose.yml``. The
suite skips rather than fails when that stack is not up, because a red suite
should mean the service is wrong, not that you forgot to run docker.
"""

from __future__ import annotations

import os
import pathlib

import pytest
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DB_DSN = os.getenv("DEMO_DB_DSN", "postgresql://demo:demo@localhost:5432/demo")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _stack_is_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def pytest_collection_modifyitems(config, items):
    """Skip this directory wholesale when the demo stack is not running.

    Done as a hook rather than a marker the test modules import, because a test
    module that imports from a conftest only resolves when pytest is invoked
    from one particular directory. The hook applies no matter how the suite is
    started.
    """
    if _stack_is_up():
        return
    skip = pytest.mark.skip(
        reason="demo stack is not running -- `docker compose -f demo/docker-compose.yml up -d`"
    )
    here = str(pathlib.Path(__file__).parent)
    for item in items:
        if str(item.fspath).startswith(here):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def token() -> str:
    r = requests.post(
        f"{BASE_URL}/auth/token",
        json={"username": "qa", "password": "demo"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def api(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.base = BASE_URL
    return s


@pytest.fixture(scope="session")
def db():
    """Read-only connection used as the database oracle."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(DB_DSN)
    conn.set_session(readonly=True)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def cache():
    """Cache oracle pointed at the demo Redis."""
    from api_core.utils.redis_utils import RedisOracle

    return RedisOracle(REDIS_URL)


@pytest.fixture
def new_order(api):
    """A freshly created order, returned as the API reported it."""
    r = api.post(
        f"{api.base}/orders",
        json={"sku": "WIDGET-001", "quantity": 2, "unit_price_cents": 500},
        timeout=10,
    )
    assert r.status_code == 201, r.text
    return r.json()
