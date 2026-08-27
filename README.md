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
    repositories/     The SQL behind the endpoints, one module per entity
    migrations/       Numbered .sql files, applied in name order
  tests/              Schema tests, and endpoint tests against a real database
frontend/
  Dockerfile          Node build stage, then nginx serving the result
  src/lib/types.ts    TypeScript mirror of the pydantic schemas
  src/lib/api.ts      Typed fetch wrapper over the API
  src/lib/dom.ts      The small DOM helpers the screens share
  src/lib/format.ts   Dates, months and amount presentation
  src/layouts/        Shared page shell
  src/pages/          One screen per route
  src/styles/app.css  The whole stylesheet
  nginx.conf          Serves the static build, proxies /api to the backend
compose.yaml          db + backend + frontend, built as images
compose.dev.yaml      Overlay: bind-mounted sources, both servers reloading
```

## Screens

Four routes, each a static page whose script talks to the API from the browser:

| Route           | What it does                                                          |
| --------------- | --------------------------------------------------------------------- |
| `/`             | The category tree with each month's activity, and category management |
| `/accounts`     | Accounts with their balances; add, rename, retype, close, delete       |
| `/transactions` | The register: filter, record, recategorise, clear, delete             |
| `/payees`       | Payees with a server-side search; add, rename, delete                  |

Names are edited in place — type in the cell and leave it. Every screen shows
what the API refused a write with in the banner under its title, so a duplicate
name or a category still in use explains itself rather than failing silently.

The pages link into each other through the register's filters, which live in the
URL: `/transactions?account_id=…` and `?category_id=…&since=…&until=…` are what
the Transactions links on the other screens point at, so those views are
bookmarkable.

The register records one category per transaction. A transaction split across
several categories still lists correctly, marked `split × n` with the breakdown
in its tooltip, but is edited through the API.

Nothing beyond Astro is installed: no UI framework, no client-side router, no
state library. Each page renders its rows with the handful of helpers in
`src/lib/dom.ts`.

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
cd frontend && npm run build                # also typechecks what the pages import
```

The endpoint tests run the real SQL, so they need PostgreSQL. They use the
sibling database of `DATABASE_URL` — `vibudget_test` for the default — creating
it on first run and emptying it between tests, so the development data is left
alone. Without a reachable server they skip and the schema tests still run.

## Status

The four screens above are live against the API, whose SQL lives in
`backend/vibudget/repositories/`. Browse the generated contract at `/docs`.

Not built yet: editing a split transaction in the browser, assigning money to
categories (the backend has no budgeted amount, so the budget screen reports
activity rather than what is left to spend), and pagination past the 100 most
recent transactions a filter matches.

| Entity         | Endpoints                                                    |
| -------------- | ------------------------------------------------------------ |
| `accounts`     | list (`include_closed`), create, read, patch, delete          |
| `categories`   | list as a tree (`include_hidden`), create, read, patch, delete |
| `payees`       | list (`search`), create, read, patch, delete                  |
| `transactions` | list (filters below), create, read, patch, delete             |

Some behaviour worth knowing:

- An account reads back with `balance`, the sum of its transactions, so the
  accounts screen needs no second call.
- `GET /api/categories` returns groups with their sub-categories nested under
  `children`; a sub-category whose group is filtered out goes with it.
- `GET /api/transactions` filters on `account_id`, `payee_id`, `category_id`,
  `since` and `until`, newest first, paged with `limit` and `offset`.
- A `PATCH` only touches the fields present in the body; sending `null`
  clears one. Sending `splits` replaces them wholesale. Changing `amount` on
  its own carries a single-category transaction's one split along with it, and
  is refused for a split transaction, which has to say how the new amount
  divides up.
- Integrity is the database's job: uniqueness, foreign keys and the category
  depth guard come back as `409 conflict`, `422 invalid_reference` or
  `404 not_found` in the shape defined in `api/errors.py`.
