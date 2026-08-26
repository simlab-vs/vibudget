-- ViBudget initial schema.
--
-- Monetary amounts are stored as signed integer milliunits (1 unit = 1000
-- milliunits), never as floats. Outflows are negative, inflows positive.
--
-- Requires PostgreSQL 13+ for the built-in gen_random_uuid().

CREATE TYPE account_type AS ENUM ('cash', 'credit');

CREATE TYPE cleared_status AS ENUM ('uncleared', 'cleared', 'reconciled');

CREATE TABLE account (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    type        account_type NOT NULL,
    on_budget   boolean NOT NULL DEFAULT true,
    closed      boolean NOT NULL DEFAULT false,
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT account_name_not_blank CHECK (btrim(name) <> '')
);

CREATE UNIQUE INDEX account_name_key ON account (lower(name));

-- Two-level hierarchy: a category with parent_id IS NULL is a group, one with
-- a parent_id is a sub-category. Nesting deeper is rejected by the trigger
-- below; only sub-categories may be assigned to transactions.
CREATE TABLE category (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id   uuid REFERENCES category (id) ON DELETE RESTRICT,
    name        text NOT NULL,
    hidden      boolean NOT NULL DEFAULT false,
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT category_name_not_blank CHECK (btrim(name) <> ''),
    CONSTRAINT category_not_own_parent CHECK (parent_id <> id)
);

CREATE UNIQUE INDEX category_name_key
    ON category (COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid), lower(name));

CREATE FUNCTION category_depth_guard() RETURNS trigger AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL
       AND EXISTS (SELECT 1 FROM category WHERE id = NEW.parent_id AND parent_id IS NOT NULL)
    THEN
        RAISE EXCEPTION 'category nesting is limited to two levels';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER category_depth_guard
    BEFORE INSERT OR UPDATE OF parent_id ON category
    FOR EACH ROW EXECUTE FUNCTION category_depth_guard();

CREATE TABLE payee (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT payee_name_not_blank CHECK (btrim(name) <> '')
);

CREATE UNIQUE INDEX payee_name_key ON payee (lower(name));

CREATE TABLE transaction (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  uuid NOT NULL REFERENCES account (id) ON DELETE CASCADE,
    payee_id    uuid REFERENCES payee (id) ON DELETE RESTRICT,
    date        date NOT NULL,
    amount      bigint NOT NULL,
    memo        text,
    cleared     cleared_status NOT NULL DEFAULT 'uncleared',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX transaction_account_date_idx ON transaction (account_id, date DESC);
CREATE INDEX transaction_payee_idx ON transaction (payee_id);

-- A transaction carries one or more splits; the single-category case is a
-- transaction with exactly one split. Split amounts must sum to the parent
-- transaction amount, which the repository layer enforces on write.
CREATE TABLE transaction_split (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  uuid NOT NULL REFERENCES transaction (id) ON DELETE CASCADE,
    category_id     uuid NOT NULL REFERENCES category (id) ON DELETE RESTRICT,
    amount          bigint NOT NULL,
    memo            text
);

CREATE INDEX transaction_split_transaction_idx ON transaction_split (transaction_id);
CREATE INDEX transaction_split_category_idx ON transaction_split (category_id);

CREATE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER account_touch_updated_at BEFORE UPDATE ON account
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER category_touch_updated_at BEFORE UPDATE ON category
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER payee_touch_updated_at BEFORE UPDATE ON payee
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER transaction_touch_updated_at BEFORE UPDATE ON transaction
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
