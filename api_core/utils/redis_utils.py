"""
pytest API harness - Redis oracle

The database oracle in ``db_utils`` answers "did the write land?". This answers
a different question that no API-only test can reach: "is the cache telling the
truth about it?"

Cache bugs are the ones that survive a green suite. A service can write to
Postgres correctly, return a correct response, and still serve a stale object
to the next reader because an eviction was missed. Every assertion made through
the API agrees with itself, and the bug ships.

So the checks here are deliberately about cache *state*, not cache contents
being convenient:

    key_exists(key)          - was the entry populated at all
    ttl(key)                 - is it expiring, or was it written without a TTL
                               (a key with no expiry is a leak that looks like a
                               working cache until memory runs out)
    key_absent(key)          - was it evicted when the underlying row changed
    value_json(key)          - what exactly is being served

Usage:
    from api_core.utils.redis_utils import redis_oracle

    redis_oracle.assert_key_absent(f"order:{order_id}")
    assert redis_oracle.ttl(f"order:{order_id}") <= 60

Configured by REDIS_URL. There is no default: a suite that silently points at
the wrong cache is worse than one that refuses to start.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import allure
import redis

logger = logging.getLogger(__name__)


class RedisOracle:
    """Read-only-by-convention view of the cache, used as a second source."""

    def __init__(self, url: str | None = None):
        self._url = url or os.getenv("REDIS_URL", "")
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if not self._url:
            raise RuntimeError(
                "REDIS_URL is not set. The Redis oracle has no default target on "
                "purpose; point it at the cache belonging to the environment "
                "under test."
            )
        if self._client is None:
            self._client = redis.Redis.from_url(self._url, decode_responses=True)
        return self._client

    # -- raw reads -----------------------------------------------------------

    def key_exists(self, key: str) -> bool:
        found = bool(self.client.exists(key))
        logger.debug("redis oracle: exists(%s) -> %s", key, found)
        return found

    def ttl(self, key: str) -> int:
        """Seconds remaining. -1 means no expiry set, -2 means no such key.

        The -1 case is worth asserting against explicitly: it is a cache entry
        that will never be reclaimed, which reads as a working cache right up
        until it isn't.
        """
        return int(self.client.ttl(key))

    def value(self, key: str) -> str | None:
        return self.client.get(key)

    def value_json(self, key: str) -> Any | None:
        raw = self.value(key)
        return None if raw is None else json.loads(raw)

    # -- assertions ----------------------------------------------------------

    @allure.step("Cache key '{key}' is present")
    def assert_key_exists(self, key: str) -> None:
        assert self.key_exists(key), f"expected cache key {key!r} to exist, it did not"

    @allure.step("Cache key '{key}' was evicted")
    def assert_key_absent(self, key: str) -> None:
        assert not self.key_exists(key), (
            f"expected cache key {key!r} to have been evicted, but it is still "
            f"present and would be served to the next reader"
        )

    @allure.step("Cache key '{key}' expires within {max_seconds}s")
    def assert_has_ttl(self, key: str, max_seconds: int) -> None:
        remaining = self.ttl(key)
        if remaining == -2:
            raise AssertionError(f"cache key {key!r} does not exist")
        if remaining == -1:
            raise AssertionError(
                f"cache key {key!r} was written without an expiry; it will never "
                f"be reclaimed"
            )
        assert remaining <= max_seconds, (
            f"cache key {key!r} expires in {remaining}s, expected <= {max_seconds}s"
        )

    @allure.step("Cache and API agree on '{key}'")
    def assert_agrees_with(self, key: str, api_payload: dict, fields: list[str]) -> None:
        """The two sources must not disagree on the fields that matter.

        A disagreement here is the finding. Do not weaken it until it passes.
        """
        cached = self.value_json(key)
        assert cached is not None, f"cache key {key!r} is absent, nothing to compare"
        mismatches = {
            f: (cached.get(f), api_payload.get(f))
            for f in fields
            if cached.get(f) != api_payload.get(f)
        }
        assert not mismatches, (
            f"cache and API disagree on {key!r}: "
            + ", ".join(f"{f}: cache={c!r} api={a!r}" for f, (c, a) in mismatches.items())
        )

    def flush_test_keys(self, pattern: str) -> int:
        """Remove keys matching a pattern. For test setup only, never as a fix."""
        keys = list(self.client.scan_iter(match=pattern))
        return self.client.delete(*keys) if keys else 0


redis_oracle = RedisOracle()
