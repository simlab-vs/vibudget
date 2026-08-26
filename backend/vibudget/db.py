"""Database access: a single asyncpg pool, created at startup and closed at
shutdown by the application lifespan.

The whole app runs on one event loop, so the pool is created there once and
handed to endpoints through the ``PoolDep`` dependency.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from vibudget.config import Config

MIGRATIONS = Path(__file__).parent / "migrations"


async def create_pool(config: Config) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        config.database_url,
        min_size=config.pool_min_size,
        max_size=config.pool_max_size,
    )


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


PoolDep = Annotated[asyncpg.Pool, Depends(get_pool)]


async def get_connection(pool: PoolDep) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as connection:
        yield connection


ConnectionDep = Annotated[asyncpg.Connection, Depends(get_connection)]


async def migrate(pool: asyncpg.Pool) -> None:
    """Apply every .sql file in ``migrations/`` in name order, once each."""
    async with pool.acquire() as connection:
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migration ("
            "  name text PRIMARY KEY,"
            "  applied_at timestamptz NOT NULL DEFAULT now()"
            ")"
        )
        for path in sorted(MIGRATIONS.glob("*.sql")):
            async with connection.transaction():
                already_applied = await connection.fetchval(
                    "SELECT true FROM schema_migration WHERE name = $1", path.name
                )
                if already_applied:
                    continue
                await connection.execute(path.read_text())
                await connection.execute(
                    "INSERT INTO schema_migration (name) VALUES ($1)", path.name
                )
