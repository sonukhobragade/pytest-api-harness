"""
The point of the harness, demonstrated: assert the response, then verify the
effect somewhere the service cannot fake.

Each test names the oracle it uses. A test that only reads the API is labelled
as such, so it is obvious how little that proves on its own.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.oracle


class TestDatabaseOracle:
    """Response says it happened. The row says whether it did."""

    def test_create_order_persists_row_with_correct_total(self, api, db, new_order):
        # The API's own arithmetic is not evidence of the stored arithmetic.
        with db.cursor() as cur:
            cur.execute(
                "SELECT sku, quantity, unit_price_cents, total_cents, status "
                "FROM orders WHERE id = %s",
                (new_order["id"],),
            )
            row = cur.fetchone()

        assert row is not None, "API returned 201 but no row exists"
        sku, qty, unit, total, status = row
        assert (sku, qty, unit) == ("WIDGET-001", 2, 500)
        assert total == qty * unit, "stored total disagrees with stored components"
        assert total == new_order["total_cents"], "stored total disagrees with the response"
        assert status == "created"

    def test_rejected_order_leaves_no_row(self, api, db):
        """A 422 must not be a partial write."""
        with db.cursor() as cur:
            cur.execute("SELECT count(*) FROM orders")
            before = cur.fetchone()[0]

        r = api.post(
            f"{api.base}/orders",
            json={"sku": "WIDGET-001", "quantity": 0, "unit_price_cents": 500},
            timeout=10,
        )
        assert r.status_code == 422

        with db.cursor() as cur:
            cur.execute("SELECT count(*) FROM orders")
            after = cur.fetchone()[0]
        assert after == before, "a rejected request still wrote a row"


class TestCacheOracle:
    """The checks an API-only suite structurally cannot make."""

    def test_read_populates_cache_with_an_expiry(self, api, cache, new_order):
        key = f"order:{new_order['id']}"
        cache.client.delete(key)

        first = api.get(f"{api.base}/orders/{new_order['id']}", timeout=10).json()
        assert first["_source"] == "db"

        cache.assert_key_exists(key)
        # A key written without a TTL reads as a working cache until memory runs out.
        cache.assert_has_ttl(key, max_seconds=60)

        second = api.get(f"{api.base}/orders/{new_order['id']}", timeout=10).json()
        assert second["_source"] == "cache"

    def test_status_change_evicts_the_cached_copy(self, api, cache, new_order):
        """The bug this catches is invisible from the API alone.

        Warm the cache, change the status, and assert the stale entry is gone.
        Without the eviction the service keeps serving 'created' to every reader
        while the database says 'paid' -- and every API assertion still passes,
        because the API is consistent with itself.
        """
        oid = new_order["id"]
        key = f"order:{oid}"

        api.get(f"{api.base}/orders/{oid}", timeout=10)
        cache.assert_key_exists(key)

        r = api.patch(f"{api.base}/orders/{oid}/status", json={"status": "paid"}, timeout=10)
        assert r.status_code == 200

        cache.assert_key_absent(key)

        fresh = api.get(f"{api.base}/orders/{oid}", timeout=10).json()
        assert fresh["status"] == "paid"
        assert fresh["_source"] == "db", "served from cache after an eviction was due"

    def test_cache_and_api_agree(self, api, cache, new_order):
        oid = new_order["id"]
        payload = api.get(f"{api.base}/orders/{oid}", timeout=10).json()
        cache.assert_agrees_with(
            f"order:{oid}", payload, fields=["id", "sku", "quantity", "total_cents", "status"]
        )


class TestThreeSourcesAgree:
    def test_api_database_and_cache_do_not_disagree(self, api, db, cache, new_order):
        """Two sources catch a lie; three catch a lie plus a stale copy."""
        oid = new_order["id"]
        api_payload = api.get(f"{api.base}/orders/{oid}", timeout=10).json()

        with db.cursor() as cur:
            cur.execute("SELECT status, total_cents FROM orders WHERE id = %s", (oid,))
            db_status, db_total = cur.fetchone()

        cached = cache.value_json(f"order:{oid}")

        assert api_payload["status"] == db_status
        assert api_payload["total_cents"] == db_total
        if cached is not None:
            assert cached["status"] == db_status, "cache is serving a status the database disowns"
