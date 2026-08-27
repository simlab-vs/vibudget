# ViBudget

A small zero-based budgeting app: accounts, categories, payees and transactions.

## Stack

| Layer    | Choice                                        |
| -------- | --------------------------------------------- |
| Backend  | FastAPI + pydantic + asyncpg (no ORM)         |
| Database | PostgreSQL, schema in plain SQL migrations    |
| Frontend | Astro, statically generated                   |
| Runtime  | Docker Compose; nginx fronts the static build |

## Layout

```
backend/
  Dockerfile          Backend image; the `dev` target adds pytest and ruff
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
  Dockerfile          Node build stage, then nginx serving the result
  src/lib/types.ts    TypeScript mirror of the pydantic schemas
  src/lib/api.ts      Typed fetch wrapper over the API
  src/layouts/        Shared page shell
  src/pages/          Routes
  nginx.conf          Serves the static build, proxies /api to the backend
compose.yaml          db + backend + frontend, built as images
compose.dev.yaml      Overlay: bind-mounted sources, both servers reloading
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

## Running with Docker Compose

The quickest way to get the whole stack up, and the shape a deployment takes.
Only Docker is needed — no local Python, Node or PostgreSQL.

```bash
cp .env.example .env      # optional; every variable has a default
docker compose up --build
```

Three services come up: `db` (PostgreSQL 17), `backend` (the API) and
`frontend` (the static build behind nginx). Compose waits for the database to
pass its health check before starting the API, which applies the migrations on
startup.

The site is served at http://localhost:8080. nginx proxies `/api`, `/health`,
`/docs` and `/openapi.json` to the backend on the same origin, so the browser
never issues a cross-origin request — that is why the frontend calls `/api`
relatively rather than through an absolute URL. The API is also published
directly on http://localhost:8000 for probing with `curl`.

Ports and database credentials come from `.env`; see its Docker Compose
section. The database port is deliberately not published — only the backend
talks to it, over the compose network — so the stack cannot collide with a
PostgreSQL already running on the host. The data lives in the `db-data` volume
and survives `docker compose down`; add `-v` to discard it.

### Local development in containers

The overlay bind-mounts both source trees and swaps the two servers for their
reloading equivalents (uvicorn `--reload`, the Astro dev server):

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

The site moves to http://localhost:4321 (`DEV_WEB_PORT`), where the Astro dev
server proxies `/api` to the backend container. Editing anything under
`backend/vibudget/` or `frontend/src/` reloads in place; changing
`pyproject.toml` or `package.json` still needs a `--build`.

The overlay also publishes the database on `localhost:5433` (`DB_PORT`) and
builds the backend's `dev` target, which carries pytest and ruff:

```bash
export COMPOSE_FILE=compose.yaml:compose.dev.yaml   # saves repeating -f
docker compose exec backend python -m pytest
docker compose exec backend ruff check .
psql postgresql://vibudget:vibudget@127.0.0.1:5433/vibudget
```

## Requirements

Only Docker is needed for the Compose stack above. To run the parts directly:

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node 20+
- PostgreSQL 13+ (the schema relies on the built-in `gen_random_uuid()`)

## Running the app without Docker

### 1. Database

Either use a local PostgreSQL:

```bash
createdb vibudget
```

or borrow the one from the Compose stack, which the dev overlay publishes on
5433 so it never collides with a PostgreSQL already on 5432:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d db
```

### 2. Configuration

Settings are read from the environment; `.env.example` lists every variable with
its default. Nothing loads `.env` for you, so copy it and export it in the shell
that runs the backend:

```bash
cp .env.example .env
set -a && source .env && set +a
```

Only `DATABASE_URL` really needs changing — for the Compose database above it
is `postgresql://vibudget:vibudget@127.0.0.1:5433/vibudget`.

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

`src/lib/api.ts` always calls `/api` relatively, so the frontend needs something
in front of it that proxies to the backend — the dev server above, or the nginx
image in the Compose stack. `npm run build` writes the static files to
`frontend/dist/`, but the `npm run preview` server has no proxy of its own, so
API calls 404 there; use the Compose stack to see the built site with a live API.

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
