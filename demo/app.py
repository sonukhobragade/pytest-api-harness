"""
A small order service, written to be tested rather than to be impressive.

It exists so this harness has something real to run against: a service with a
database behind it, a cache in front of it, and enough business rules that a
test can be wrong in an interesting way.

Three things here are deliberate, because they are what the harness demonstrates:

1. Writes land in Postgres. A 201 is not proof; the row is.
2. Reads are cached in Redis with a TTL, and a status change evicts that key.
   Cache invalidation is where real services quietly serve stale data, and it is
   invisible to any test that only reads the API.
3. Status changes follow a state machine. Illegal transitions are refused with
   409, which gives state-transition tests something to actually assert.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import redis
from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel, Field, field_validator

DB_DSN = os.getenv("DEMO_DB_DSN", "postgresql://demo:demo@localhost:5432/demo")
REDIS_URL = os.getenv("DEMO_REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("DEMO_CACHE_TTL", "60"))
DEMO_TOKEN = os.getenv("DEMO_TOKEN", "demo-token")

# created -> paid -> shipped -> delivered, with cancellation allowed until it
# ships. Anything else is a 409 rather than a silent no-op.
TRANSITIONS = {
    "created": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}

app = FastAPI(title="demo order service")
_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@contextmanager
def db():
    conn = psycopg2.connect(DB_DSN)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def require_token(authorization: str = Header(default="")):
    if authorization != f"Bearer {DEMO_TOKEN}":
        raise HTTPException(status_code=401, detail="bad or missing token")


class TokenRequest(BaseModel):
    username: str
    password: str


class OrderRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=32)
    # 1..100 inclusive. The bounds are the point: they give boundary-value tests
    # something exact to sit on.
    quantity: int = Field(ge=1, le=100)
    unit_price_cents: int = Field(ge=1, le=1_000_000)

    @field_validator("sku")
    @classmethod
    def sku_is_uppercase_alnum(cls, v: str) -> str:
        if not v.replace("-", "").isalnum() or v != v.upper():
            raise ValueError("sku must be uppercase alphanumeric, hyphens allowed")
        return v


class StatusRequest(BaseModel):
    status: str


def cache_key(order_id: int) -> str:
    return f"order:{order_id}"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/token")
def token(body: TokenRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=422, detail="username and password required")
    if body.password != "demo":
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"access_token": DEMO_TOKEN, "token_type": "bearer", "expires_in": 3600}


@app.post("/orders", status_code=201, dependencies=[Depends(require_token)])
def create_order(body: OrderRequest):
    total = body.quantity * body.unit_price_cents
    with db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO orders (sku, quantity, unit_price_cents, total_cents, status) "
                "VALUES (%s, %s, %s, %s, 'created') RETURNING *",
                (body.sku, body.quantity, body.unit_price_cents, total),
            )
            row = cur.fetchone()
    return dict(row)


@app.get("/orders/{order_id}", dependencies=[Depends(require_token)])
def get_order(order_id: int):
    """Read-through cache. A hit is served from Redis and never touches Postgres."""
    cached = _redis.get(cache_key(order_id))
    if cached:
        payload = json.loads(cached)
        payload["_source"] = "cache"
        return payload

    with db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no such order")

    payload = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
    _redis.setex(cache_key(order_id), CACHE_TTL_SECONDS, json.dumps(payload))
    payload["_source"] = "db"
    return payload


@app.patch("/orders/{order_id}/status", dependencies=[Depends(require_token)])
def set_status(order_id: int, body: StatusRequest):
    if body.status not in TRANSITIONS:
        raise HTTPException(status_code=422, detail=f"unknown status {body.status!r}")

    with db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (order_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="no such order")
            if body.status not in TRANSITIONS[row["status"]]:
                raise HTTPException(
                    status_code=409,
                    detail=f"cannot move from {row['status']} to {body.status}",
                )
            cur.execute(
                "UPDATE orders SET status = %s, updated_at = now() WHERE id = %s RETURNING *",
                (body.status, order_id),
            )
            updated = cur.fetchone()

    # Evict, so the next read reflects the change. Comment this line out and the
    # API tests still pass while the cache serves the old status -- which is the
    # whole argument for a second oracle.
    _redis.delete(cache_key(order_id))
    return dict(updated)


@app.get("/catalog/{sku}", dependencies=[Depends(require_token)])
def catalog(sku: str):
    key = f"catalog:{sku}"
    cached = _redis.get(key)
    if cached:
        return {"sku": sku, "price_cents": int(cached), "_source": "cache"}
    price = 100 + sum(ord(c) for c in sku)  # deterministic stand-in for a lookup
    _redis.setex(key, CACHE_TTL_SECONDS, price)
    time.sleep(0.05)  # a cache miss should be visibly slower than a hit
    return {"sku": sku, "price_cents": price, "_source": "db"}
