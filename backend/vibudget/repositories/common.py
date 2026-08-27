"""Helpers shared by the repository modules.

The database is the authority on integrity: uniqueness, foreign keys and the
category depth guard all live in ``migrations/001_initial.sql``. Rather than
re-check those rules in Python before every write, the repositories run the
write and translate whatever the database objects to into the domain
exceptions from :mod:`vibudget.api.errors`.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import Enum
from typing import Any

import asyncpg

from vibudget.api.errors import Conflict, InvalidReference

# Foreign keys are named after the column they constrain; this maps the ones a
# client can trip to the entity a caller would recognise in the message.
REFERENCED_ENTITY = {
    "category_parent_id_fkey": "category",
    "transaction_account_id_fkey": "account",
    "transaction_payee_id_fkey": "payee",
    "transaction_split_category_id_fkey": "category",
    "transaction_split_transaction_id_fkey": "transaction",
}


@contextmanager
def translate_writes(entity: str) -> Iterator[None]:
    """Turn the integrity errors of an insert or update into domain exceptions."""
    try:
        yield
    except asyncpg.UniqueViolationError as error:
        raise Conflict(f"another {entity} already has that name") from error
    except asyncpg.ForeignKeyViolationError as error:
        referenced = REFERENCED_ENTITY.get(error.constraint_name or "", "row")
        raise InvalidReference(f"the referenced {referenced} does not exist") from error
    except asyncpg.CheckViolationError as error:
        raise Conflict(f"the {entity} violates {error.constraint_name}") from error
    except asyncpg.RaiseError as error:
        # A guard raised by a plpgsql trigger, e.g. category nesting depth.
        raise Conflict(str(error)) from error


@contextmanager
def translate_delete(message: str) -> Iterator[None]:
    """Turn a delete refused by an ON DELETE RESTRICT reference into a conflict."""
    try:
        yield
    except asyncpg.ForeignKeyViolationError as error:
        raise Conflict(message) from error


def assignments(values: Mapping[str, Any]) -> tuple[str, list[Any]]:
    """Render the set fields of a partial update as a SQL SET clause.

    Returns the clause and its arguments, numbered from $1 so the caller can
    append its own parameters after them.
    """
    clause = ", ".join(f"{column} = ${index}" for index, column in enumerate(values, 1))
    return clause, [encodable(value) for value in values.values()]


def encodable(value: Any) -> Any:
    """asyncpg encodes a PostgreSQL enum from a plain str, not an ``Enum``."""
    return value.value if isinstance(value, Enum) else value
