CREATE TABLE IF NOT EXISTS orders (
    id               SERIAL PRIMARY KEY,
    sku              TEXT        NOT NULL,
    quantity         INTEGER     NOT NULL CHECK (quantity BETWEEN 1 AND 100),
    unit_price_cents INTEGER     NOT NULL CHECK (unit_price_cents > 0),
    total_cents      INTEGER     NOT NULL,
    status           TEXT        NOT NULL DEFAULT 'created',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The harness connects with this role for its database oracle. It is read-only
-- on purpose: an oracle that can write is not an independent check, it is a
-- second way to cause the bug you are looking for.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oracle') THEN
        CREATE ROLE oracle LOGIN PASSWORD 'oracle';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE demo TO oracle;
GRANT USAGE ON SCHEMA public TO oracle;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO oracle;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO oracle;
