"""Runtime configuration, read from the environment."""

import os
from dataclasses import dataclass


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Config:
    database_url: str
    pool_min_size: int = 1
    pool_max_size: int = 10
    debug: bool = False
    migrate_on_startup: bool = True

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            database_url=os.environ.get("DATABASE_URL", "postgresql://localhost/vibudget"),
            pool_min_size=int(os.environ.get("DB_POOL_MIN_SIZE", 1)),
            pool_max_size=int(os.environ.get("DB_POOL_MAX_SIZE", 10)),
            debug=_flag("VIBUDGET_DEBUG"),
            migrate_on_startup=_flag("VIBUDGET_MIGRATE_ON_STARTUP", default=True),
        )
