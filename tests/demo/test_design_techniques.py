"""
Black-box test design applied to the demo service.

Every class here is one of the standard techniques (ISTQB Foundation, "Test
Design Techniques"). They are named because the naming is the useful part: it
turns "we wrote some tests" into a coverage argument you can defend in a review
-- what was covered, by which technique, and what that technique deliberately
leaves out.

    Equivalence partitioning  - one case per class of input, not fifty from one class
    Boundary value analysis   - the values either side of every limit
    Decision table            - each combination of conditions that changes behaviour
    State transition          - legal moves, and the illegal ones being refused
    Error guessing            - the malformed inputs experience says break parsers
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.design

VALID = {"sku": "WIDGET-001", "quantity": 2, "unit_price_cents": 500}


def order(**overrides):
    return {**VALID, **overrides}


class TestEquivalencePartitioning:
    """One representative per class. More cases from the same class add runtime,
    not coverage."""

    @pytest.mark.parametrize(
        "quantity,expected,partition",
        [
            (-1, 422, "below range"),
            (0, 422, "below range boundary"),
            (50, 201, "within range"),
            (500, 422, "above range"),
        ],
        ids=["negative", "zero", "valid", "too-large"],
    )
    def test_quantity_partitions(self, api, quantity, expected, partition):
        r = api.post(f"{api.base}/orders", json=order(quantity=quantity), timeout=10)
        assert r.status_code == expected, f"{partition}: {r.status_code} -> {r.text[:120]}"

    @pytest.mark.parametrize(
        "sku,expected",
        [
            ("WIDGET-001", 201),   # uppercase alphanumeric with hyphen
            ("WIDGET001", 201),    # no hyphen
            ("widget-001", 422),   # lowercase rejected
            ("WIDGET_001", 422),   # underscore is not a permitted separator
            ("WIDGET 001", 422),   # whitespace
            ("", 422),             # empty
        ],
    )
    def test_sku_format_partitions(self, api, sku, expected):
        r = api.post(f"{api.base}/orders", json=order(sku=sku), timeout=10)
        assert r.status_code == expected, f"sku={sku!r} -> {r.status_code}"


class TestBoundaryValueAnalysis:
    """Off-by-one lives at the edge, so test the edge and one step either side."""

    @pytest.mark.parametrize(
        "quantity,expected",
        [(0, 422), (1, 201), (2, 201), (99, 201), (100, 201), (101, 422)],
        ids=["min-1", "min", "min+1", "max-1", "max", "max+1"],
    )
    def test_quantity_boundaries(self, api, quantity, expected):
        r = api.post(f"{api.base}/orders", json=order(quantity=quantity), timeout=10)
        assert r.status_code == expected

    @pytest.mark.parametrize(
        "price,expected",
        [(0, 422), (1, 201), (1_000_000, 201), (1_000_001, 422)],
        ids=["min-1", "min", "max", "max+1"],
    )
    def test_unit_price_boundaries(self, api, price, expected):
        r = api.post(f"{api.base}/orders", json=order(unit_price_cents=price), timeout=10)
        assert r.status_code == expected

    def test_maximum_order_total_is_computed_correctly(self, api, db):
        """The largest legal order is where an integer overflow would show."""
        r = api.post(
            f"{api.base}/orders",
            json=order(quantity=100, unit_price_cents=1_000_000),
            timeout=10,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["total_cents"] == 100 * 1_000_000

        with db.cursor() as cur:
            cur.execute("SELECT total_cents FROM orders WHERE id = %s", (body["id"],))
            assert cur.fetchone()[0] == 100 * 1_000_000, "stored total overflowed or truncated"


class TestDecisionTable:
    """Auth x payload validity. Each row is a combination that changes the outcome.

    | token   | payload | expected |
    |---------|---------|----------|
    | valid   | valid   | 201      |
    | valid   | invalid | 422      |
    | missing | valid   | 401      |
    | missing | invalid | 401      |  <- auth is checked first; 401 beats 422

    That last row is the one worth having. It pins the ORDER of the checks, and
    the order is a real decision: replying 422 to an unauthenticated caller tells
    them which payloads are valid.
    """

    @pytest.mark.parametrize(
        "with_token,payload,expected",
        [
            (True, VALID, 201),
            (True, {**VALID, "quantity": 0}, 422),
            (False, VALID, 401),
            (False, {**VALID, "quantity": 0}, 401),
        ],
        ids=["auth+valid", "auth+invalid", "noauth+valid", "noauth+invalid"],
    )
    def test_auth_and_validation_combinations(self, api, with_token, payload, expected):
        headers = {} if with_token else {"Authorization": ""}
        r = api.post(f"{api.base}/orders", json=payload, headers=headers, timeout=10)
        assert r.status_code == expected


class TestStateTransition:
    """created -> paid -> shipped -> delivered, cancellable until it ships.

    Legal moves are the easy half. The half that finds bugs is asserting the
    illegal ones are refused, because an unguarded state machine tends to accept
    anything and leave the data in a state nothing downstream expects.
    """

    LEGAL = [
        ("created", "paid"),
        ("created", "cancelled"),
        ("paid", "shipped"),
        ("paid", "cancelled"),
        ("shipped", "delivered"),
    ]
    ILLEGAL = [
        ("created", "shipped"),     # skipping payment
        ("created", "delivered"),   # skipping everything
        ("shipped", "cancelled"),   # too late to cancel
        ("delivered", "paid"),      # backwards
        ("cancelled", "paid"),      # resurrection
    ]

    def _drive_to(self, api, state):
        """Walk a fresh order to the requested state through legal moves only."""
        oid = api.post(f"{api.base}/orders", json=VALID, timeout=10).json()["id"]
        path = {
            "created": [],
            "paid": ["paid"],
            "shipped": ["paid", "shipped"],
            "delivered": ["paid", "shipped", "delivered"],
            "cancelled": ["cancelled"],
        }[state]
        for step in path:
            r = api.patch(f"{api.base}/orders/{oid}/status", json={"status": step}, timeout=10)
            assert r.status_code == 200, f"setup move to {step} failed: {r.text[:120]}"
        return oid

    @pytest.mark.parametrize("start,target", LEGAL, ids=[f"{a}->{b}" for a, b in LEGAL])
    def test_legal_transitions_are_accepted(self, api, start, target):
        oid = self._drive_to(api, start)
        r = api.patch(f"{api.base}/orders/{oid}/status", json={"status": target}, timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == target

    @pytest.mark.parametrize("start,target", ILLEGAL, ids=[f"{a}->{b}" for a, b in ILLEGAL])
    def test_illegal_transitions_are_refused(self, api, db, start, target):
        oid = self._drive_to(api, start)
        r = api.patch(f"{api.base}/orders/{oid}/status", json={"status": target}, timeout=10)
        assert r.status_code == 409, f"{start}->{target} was accepted"

        # A refusal must also not have written. 409 plus a mutated row is worse
        # than either alone, and only the database can tell you.
        with db.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE id = %s", (oid,))
            assert cur.fetchone()[0] == start, "refused transition still changed the row"


class TestErrorGuessing:
    """No formal derivation. These are the shapes that historically break parsers."""

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({}, 422),
            ({"sku": "WIDGET-001"}, 422),
            (order(quantity="2"), 201),          # numeric string is coerced
            (order(quantity=2.5), 422),          # non-integer
            (order(quantity=None), 422),
            (order(sku="A" * 33), 422),          # over max_length
            (order(**{"unit_price_cents": -1}), 422),
        ],
        ids=["empty", "missing-fields", "numeric-string", "float", "null",
             "sku-too-long", "negative-price"],
    )
    def test_malformed_payloads_are_refused_cleanly(self, api, payload, expected):
        r = api.post(f"{api.base}/orders", json=payload, timeout=10)
        assert r.status_code == expected, f"{payload} -> {r.status_code}"
        assert r.status_code != 500, "malformed input reached an unhandled error"

    def test_unknown_order_is_404_not_500(self, api):
        r = api.get(f"{api.base}/orders/99999999", timeout=10)
        assert r.status_code == 404

    def test_unknown_status_is_refused(self, api, new_order):
        r = api.patch(
            f"{api.base}/orders/{new_order['id']}/status",
            json={"status": "teleported"},
            timeout=10,
        )
        assert r.status_code == 422
