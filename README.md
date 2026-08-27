# ViBudget

A small zero-based budgeting app: accounts, categories, payees and transactions.

## Stack

| Layer    | Choice                                        |
| -------- | --------------------------------------------- |
| Backend  | FastAPI + pydantic + asyncpg (no ORM)         |
| Database | PostgreSQL, schema in plain SQL migrations    |
| Frontend | Astro, statically generated                   |

## Layout

```
backend/
  vibudget/
    app.py            FastAPI factory; the pool lives in the lifespan hook
    config.py         Environment-driven settings
    db.py             asyncpg pool, request dependencies, migration runner
    cli.py            `vibudget serve` / `vibudget migrate`
    schemas/          Pydantic models, one module per entity
    api/              One router per entity, mounted under /api
    migrations/       Numbered .sql files, applied in name order
  tests/
frontend/
  src/lib/types.ts    TypeScript mirror of the pydantic schemas
  src/lib/api.ts      Typed fetch wrapper over the API
  src/layouts/        Shared page shell
  src/pages/          Routes
```

## Data model

Money is stored as **signed integer milliunits** (1 unit = 1000 milliunits) so that
no amount ever passes through a float. Outflows are negative, inflows positive.

- **Account** — `cash` or `credit`, on- or off-budget, closable.
- **Category** — a two-level tree. A category with no parent is a *group*; one with a
  parent is a *sub-category*. Only sub-categories are assignable to transactions, and
  a database trigger rejects deeper nesting.
- **Payee** — a name, unique case-insensitively.
- **Transaction** — belongs to one account and at most one payee, and carries one or
  more **splits**. The single-category case is a transaction with exactly one split;
  split amounts always sum to the transaction amount.

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node 20+
- PostgreSQL 13+ (the schema relies on the built-in `gen_random_uuid()`)

## Running the app

### 1. Database

Either use a local PostgreSQL:

```bash
createdb vibudget
```

or run one in Docker:

```bash
docker run -d --name vibudget-db \
  -e POSTGRES_USER=vibudget -e POSTGRES_PASSWORD=vibudget -e POSTGRES_DB=vibudget \
  -p 5432:5432 postgres:17-alpine
```

### 2. Configuration

Settings are read from the environment; `.env.example` lists every variable with
its default. Nothing loads `.env` for you, so copy it and export it in the shell
that runs the backend:

```bash
cp .env.example .env
set -a && source .env && set +a
```

Only `DATABASE_URL` really needs changing — for the Docker container above it is
`postgresql://vibudget:vibudget@127.0.0.1:5432/vibudget`.

### 3. Backend

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
.venv/bin/vibudget migrate          # apply backend/vibudget/migrations/*.sql
.venv/bin/vibudget serve --reload
```

The API listens on http://127.0.0.1:8000; the generated OpenAPI docs are at
http://127.0.0.1:8000/docs and `GET /health` should answer `{"status": "ok"}`.

`vibudget serve` also accepts `--host` and `--port`. Migrations are applied on
startup as well unless `VIBUDGET_MIGRATE_ON_STARTUP=false`, so the explicit
`vibudget migrate` step is mostly useful for setting the database up on its own.

### 4. Frontend

In a second terminal, with the backend running:

```bash
cd frontend
npm install
npm run dev
```

The site is served at http://localhost:4321. The dev server proxies `/api` to
`VIBUDGET_API_URL` (default http://127.0.0.1:8000).

For a production build, `npm run build` writes static files to `frontend/dist/`
and `npm run preview` serves them.

## Development

```bash
cd backend && .venv/bin/python -m pytest    # tests
cd backend && .venv/bin/ruff check .        # lint
cd frontend && npm run check                # Astro + TypeScript check
```

## Status

The schemas, migrations, routing surface and error handling are in place; every
endpoint currently raises `NotImplementedError` pending the repository layer.
Browse the generated contract at `/docs`.
