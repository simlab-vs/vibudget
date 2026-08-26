"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from vibudget.api import api
from vibudget.api.errors import register_exception_handlers
from vibudget.config import Config
from vibudget.db import create_pool, migrate


def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = config
        app.state.pool = await create_pool(config)
        if config.migrate_on_startup:
            await migrate(app.state.pool)
        try:
            yield
        finally:
            await app.state.pool.close()

    app = FastAPI(
        title="ViBudget",
        version="0.1.0",
        summary="Accounts, categories, payees and transactions for a zero-based budget.",
        lifespan=lifespan,
        debug=config.debug,
    )

    app.include_router(api)
    register_exception_handlers(app)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
