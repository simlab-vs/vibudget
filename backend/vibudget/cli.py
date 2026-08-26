"""Command line entry points."""

import argparse
import asyncio

import uvicorn

from vibudget.config import Config
from vibudget.db import create_pool, migrate


def main() -> None:
    parser = argparse.ArgumentParser(prog="vibudget")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Run the API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    commands.add_parser("migrate", help="Apply pending database migrations")

    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run("vibudget.app:app", host=args.host, port=args.port, reload=args.reload)
    elif args.command == "migrate":
        asyncio.run(_migrate())


async def _migrate() -> None:
    pool = await create_pool(Config.from_env())
    try:
        await migrate(pool)
    finally:
        await pool.close()
    print("migrations applied")


if __name__ == "__main__":
    main()
