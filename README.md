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

## Getting started

```bash
# Database
createdb vibudget
cp .env.example .env

# Backend
cd backend
uv venv && uv pip install -e ".[dev]"
.venv/bin/vibudget migrate
.venv/bin/vibudget serve --reload     # http://127.0.0.1:8000/docs

# Frontend
cd frontend
npm install
npm run dev                            # http://localhost:4321
```

Run the tests with `cd backend && .venv/bin/python -m pytest`.

## Status

The schemas, migrations, routing surface and error handling are in place; every
endpoint currently raises `NotImplementedError` pending the repository layer.
Browse the generated contract at `/docs`.
