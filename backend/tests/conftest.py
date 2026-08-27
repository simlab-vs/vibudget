"""Fixtures for the endpoint tests.

These exercise the real SQL, so they need PostgreSQL. To leave the development
database alone they run against a sibling database named after it with a
``_test`` suffix, created on first use; with no server reachable they skip.
"""

from dataclasses import replace

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from vibudget.app import create_app
from vibudget.config import Config

TABLES = "account, category, payee, transaction, transaction_split"


def sibling_database(url: str) -> tuple[str, str]:
    """Point a connection URL at the sibling ``_test`` database."""
    prefix, _, name = url.rpartition("/")
    return f"{prefix}/{name}_test", f"{name}_test"


async def ensure_database(config: Config) -> Config:
    url, name = sibling_database(config.database_url)
    try:
        connection = await asyncpg.connect(config.database_url)
    except (OSError, asyncpg.PostgresError) as error:
        pytest.skip(f"no PostgreSQL behind DATABASE_URL: {error}")

    try:
        if not await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
            await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()
    return replace(config, database_url=url, migrate_on_startup=True)


@pytest.fixture
async def client() -> AsyncClient:
    """An HTTP client onto a freshly emptied database.

    The lifespan context is entered by hand because ASGITransport does not run
    it, and it is what creates the pool and applies the migrations.
    """
    app = create_app(await ensure_database(Config.from_env()))
    async with app.router.lifespan_context(app):
        await app.state.pool.execute(f"TRUNCATE {TABLES} CASCADE")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
