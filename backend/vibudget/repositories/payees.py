"""Payee rows."""

from uuid import UUID

import asyncpg

from vibudget.api.errors import NotFound
from vibudget.repositories.common import assignments, translate_delete, translate_writes
from vibudget.schemas import Payee, PayeeCreate, PayeeUpdate


async def list_payees(
    connection: asyncpg.Connection, *, search: str | None = None
) -> list[Payee]:
    rows = await connection.fetch(
        "SELECT * FROM payee"
        " WHERE ($1::text IS NULL OR name ILIKE '%' || $1 || '%')"
        " ORDER BY lower(name)",
        search,
    )
    return [Payee(**row) for row in rows]


async def get_payee(connection: asyncpg.Connection, payee_id: UUID) -> Payee:
    row = await connection.fetchrow("SELECT * FROM payee WHERE id = $1", payee_id)
    if row is None:
        raise NotFound("payee", payee_id)
    return Payee(**row)


async def create_payee(connection: asyncpg.Connection, payload: PayeeCreate) -> Payee:
    with translate_writes("payee"):
        row = await connection.fetchrow(
            "INSERT INTO payee (name) VALUES ($1) RETURNING *", payload.name
        )
    return Payee(**row)


async def update_payee(
    connection: asyncpg.Connection, payee_id: UUID, payload: PayeeUpdate
) -> Payee:
    clause, values = assignments(payload.model_dump(exclude_unset=True))
    if not clause:
        return await get_payee(connection, payee_id)

    with translate_writes("payee"):
        row = await connection.fetchrow(
            f"UPDATE payee SET {clause} WHERE id = ${len(values) + 1} RETURNING *",
            *values,
            payee_id,
        )
    if row is None:
        raise NotFound("payee", payee_id)
    return Payee(**row)


async def delete_payee(connection: asyncpg.Connection, payee_id: UUID) -> None:
    with translate_delete("the payee is still named by one or more transactions"):
        deleted = await connection.execute("DELETE FROM payee WHERE id = $1", payee_id)
    if deleted == "DELETE 0":
        raise NotFound("payee", payee_id)
