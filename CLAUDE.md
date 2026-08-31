# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ViBudget is a zero-based budgeting app: accounts, categories, payees, transactions.
`AGENTS.md` states the product intent and the domain rules; this file covers how the
code is put together and how to work in it. `README.md` has the full run instructions.

## Commands

The dev stack (bind-mounted sources, uvicorn `--reload` and the Astro dev server):

```bash
export COMPOSE_FILE=compose.yaml:compose.dev.yaml   # saves repeating -f on every call
docker compose up --build -d        # site on :4321, API on :8000, db on :5433
docker compose logs -f backend frontend
docker compose down                 # add -v to discard the db-data volume
```

### The demo budget

`scripts/seed_demo.sql` loads a realistic two-year budget — 4 accounts, a nine-group
category tree, 35 payees, ~670 transactions to August 2026 — and it is what everyone
develops against, so a screen is exercised at a realistic volume rather than against
three rows. Compose runs it as a one-off `seed` service after the backend passes its
health check, and the frontend waits for it to complete; the **dev overlay inherits
that**, so `up` seeds there too.

The script is data only (its helper lives in `pg_temp`, so nothing survives the session)
and **idempotent by bail-out**: it does nothing at all if `account`, `payee` or
`transaction` holds a single row. That has one consequence worth knowing — you cannot
top up or refresh the demo data, and a half-deleted budget stays half-deleted. Resetting
means discarding the volume:

```bash
docker compose down -v && docker compose up --build -d   # destroys the budget for good
```

The seed never touches the `_test` sibling database, so the endpoint tests are unaffected
by it and keep starting from empty.

Backend, from `backend/` (the venv is created with `uv venv && uv pip install -e ".[dev]"`):

```bash
.venv/bin/python -m pytest                                    # whole suite
.venv/bin/python -m pytest tests/test_api.py::test_account_round_trip   # one test
.venv/bin/python -m pytest -k split                           # by name
.venv/bin/ruff check .          # lint; ruff format is not part of the workflow
```

Frontend, from `frontend/`:

```bash
npm run check     # astro check: the typecheck to run before calling a change done
npm run build     # also typechecks whatever the pages import
```

The endpoint tests run the real SQL against the **sibling** database of `DATABASE_URL`
(`vibudget_test` for the default), created on first run and truncated between tests, so
they never touch development data. With no server reachable they *skip* rather than fail —
a green run that skipped everything proves nothing. Running them on the host needs the
compose database:

```bash
export DATABASE_URL=postgresql://vibudget:vibudget@127.0.0.1:5433/vibudget
```

The `.env` default (`postgresql://localhost/vibudget`) assumes a PostgreSQL on the host;
nothing loads `.env` for you (`set -a && source .env && set +a`), and Compose builds the
backend container's URL from `POSTGRES_*` regardless.

## The backend/frontend contract

Three things cross the boundary. Changing any of them is a change both teams feel, so say
so in the PR rather than letting the other side discover it at runtime.

1. **`frontend/src/lib/types.ts` mirrors `backend/vibudget/schemas/` by hand.** There is no
   codegen. A field added to a pydantic schema does not exist for the frontend until it is
   added to the TypeScript interface too; the two drift silently otherwise.
2. **The error shape**, defined in `backend/vibudget/api/errors.py` and consumed by
   `frontend/src/lib/api.ts`: `{"error": ..., "message": ...}` at 404 `not_found`,
   409 `conflict`, 422 `invalid_reference`. FastAPI's own validation failures arrive as
   `detail` instead, which `api.ts` also unwraps. The screens show `message` verbatim in
   the banner, so it is user-facing text — write it for a person, in lower case, saying
   what was refused.
3. **The API is same-origin.** `api.ts` sets `BASE_URL = ""` and calls `/api` relatively;
   the Astro dev server proxies `/api` to `VIBUDGET_API_URL`, nginx does the same in the
   built image. Never introduce an absolute API URL or a CORS layer — fix the proxy instead.
   `npm run preview` has no proxy, so API calls 404 there; use the Compose stack.

## Architecture

A request goes: **page script → `lib/api.ts` → `/api` proxy → router → repository → SQL**.

### Backend (`backend/vibudget/`)

- `app.py` — the factory. The asyncpg pool is created in the **lifespan hook** (one event
  loop, one pool) and reaches endpoints through `ConnectionDep` from `db.py`. Migrations
  run at startup unless `VIBUDGET_MIGRATE_ON_STARTUP=false`.
- `api/` — one router per entity, thin: it declares the HTTP surface and delegates. All are
  mounted under `/api` by the loop in `api/__init__.py`; **a new router must be added to
  that tuple** or it silently does not exist.
- `repositories/` — the SQL, one module per entity. Hand-written asyncpg; **no ORM, no
  SQLAlchemy** (deliberate, see `AGENTS.md`).
- `schemas/` — pydantic. Three shapes per entity: `XCreate` (writes), `XUpdate` (partial
  writes, every field optional), `X` (a row read back, extending `Record` with
  `id`/`created_at`/`updated_at`). All re-exported from `schemas/__init__.py` — **add new
  names there** as well as to `__all__`.
- `migrations/*.sql` — numbered plain SQL, applied in name order, each recorded once in
  `schema_migration`. **Never edit an applied migration**; add the next number. The schema
  is the source of truth the pydantic models mirror.

**The database owns integrity, not Python.** Uniqueness (case-insensitive on name),
foreign keys and the category depth trigger live in the migration. Repositories run the
write and let `translate_writes` / `translate_delete` in `repositories/common.py` turn
whatever PostgreSQL objects to into a domain exception. Do not add a pre-flight `SELECT`
to check a rule the schema already enforces — but **a new foreign key needs its constraint
name in `REFERENCED_ENTITY`**, or its violations come back as a vague "row".

`assignments()` in the same module renders a partial update into a `SET` clause from
`model_dump(exclude_unset=True)`. That is what makes `PATCH` touch only the fields present
in the body while an explicit `null` clears one — preserve that distinction in new
endpoints.

### Frontend (`frontend/src/`)

Astro, `output: "static"`, and **nothing else**: no UI framework, no client-side router, no
state library. Each of the four routes is a `.astro` page whose markup is static and whose
inline `<script>` module fetches and renders in the browser. Imports use the `@/*` alias
onto `src/`.

- `lib/api.ts` — the typed fetch wrapper. Every call goes through it; nothing else calls `fetch`.
- `lib/dom.ts` — the glue that replaces a framework: `el()` builds nodes, `element()` looks
  one up or throws, `replace()` swaps children, `fillSelect()` refills a select keeping the
  current choice.
- `lib/format.ts` and `formatMilliunits()` in `types.ts` — dates, months, amounts.
- `layouts/Base.astro` — the shell, the nav (**a new route needs an entry in `sections`**)
  and the `#status` banner every screen writes into.

The error convention on a screen: `resetStatus()` on the way into a gesture, then
`attempt(() => api...)`, which on failure paints the API's message into the banner and
returns `undefined`. A refused write leaves the banner standing so the reload that follows
does not wipe the explanation. Follow it — a screen that swallows a rejection looks broken.

Names are edited in place: an `onchange` on the cell input sends the `PATCH`, then reloads.

## Domain rules that bite

- **Money is signed integer milliunits** (1 unit = 1000). Outflows negative, inflows
  positive. `bigint` in SQL, `int` in pydantic, `number` in TS. No amount ever becomes a
  float; convert only at the display edge (`formatMilliunits`, `to_milliunits`).
- **Every transaction has at least one split**, and splits always sum to the amount. The
  single-category case is one split. The pydantic validators enforce the sum on the way in;
  `create`/`update` write both tables in one database transaction on the way out.
  Sending `splits` on a `PATCH` requires sending `amount` too, and replaces them wholesale.
  Changing `amount` alone carries a single-split transaction's split along; on a split
  transaction it is a 409.
- **Only sub-categories are assignable.** A category with no `parent_id` is a group; the
  `category_depth_guard` trigger rejects a third level, and `_reject_unassignable` in the
  transactions repository refuses a split pointing at a group.
- Deletes: an account cascades to its transactions and their splits; a category or payee
  still referenced is refused (`ON DELETE RESTRICT`) and surfaces as a 409.

## Working across the two teams

- Branch per feature off `main`, merged by PR. Commits are conventional and scoped the way
  the split runs: `feat(api): …`, `feat(frontend): …`, `feat(docker): …`, `docs: …`.
- A feature that spans both usually lands as: migration + schemas + repository + router
  (+ endpoint tests) on the backend, then `types.ts` + `api.ts` + the screen on the
  frontend. The frontend can start against the shape in `/docs` — the OpenAPI contract is
  generated from the pydantic schemas, so it is accurate the moment the backend PR merges.
- Endpoint tests go through HTTP (`AsyncClient` against the real app) rather than calling
  repositories, and the helpers at the top of `tests/test_api.py` (`create`, `budget`) are
  how a fixture budget is set up. Follow that shape.
- Not built yet, so do not assume it exists: editing a split transaction in the browser,
  budgeted amounts (the backend has no such column — the budget screen reports *activity*,
  not what is left to spend), pagination past a filter's 100 most recent transactions.
