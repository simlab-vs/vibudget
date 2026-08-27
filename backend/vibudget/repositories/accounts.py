"""Account rows, read back with the balance their transactions add up to."""

from uuid import UUID

import asyncpg

from vibudget.api.errors import NotFound
from vibudget.repositories.common import assignments, translate_writes
from vibudget.schemas import Account, AccountCreate, AccountUpdate


def _balance(alias: str) -> str:
    return (
        f"COALESCE((SELECT sum(amount) FROM transaction WHERE account_id = {alias}.id), 0)"
        " AS balance"
    )


_SELECT = f"SELECT account.*, {_balance('account')} FROM account"


async def list_accounts(
    connection: asyncpg.Connection, *, include_closed: bool = False
) -> list[Account]:
    rows = await connection.fetch(
        f"{_SELECT} WHERE ($1 OR NOT account.closed) ORDER BY lower(account.name)",
        include_closed,
    )
    return [Account(**row) for row in rows]


async def get_account(connection: asyncpg.Connection, account_id: UUID) -> Account:
    row = await connection.fetchrow(f"{_SELECT} WHERE account.id = $1", account_id)
    if row is None:
        raise NotFound("account", account_id)
    return Account(**row)


async def create_account(connection: asyncpg.Connection, payload: AccountCreate) -> Account:
    with translate_writes("account"):
        row = await connection.fetchrow(
            "INSERT INTO account (name, type, on_budget, note)"
            " VALUES ($1, $2, $3, $4) RETURNING *",
            payload.name,
            payload.type.value,
            payload.on_budget,
            payload.note,
        )
    return Account(**row, balance=0)


async def update_account(
    connection: asyncpg.Connection, account_id: UUID, payload: AccountUpdate
) -> Account:
    clause, values = assignments(payload.model_dump(exclude_unset=True))
    if not clause:
        return await get_account(connection, account_id)

    with translate_writes("account"):
        row = await connection.fetchrow(
            f"WITH updated AS ("
            f"  UPDATE account SET {clause} WHERE id = ${len(values) + 1} RETURNING *"
            f") SELECT updated.*, {_balance('updated')} FROM updated",
            *values,
            account_id,
        )
    if row is None:
        raise NotFound("account", account_id)
    return Account(**row)


async def delete_account(connection: asyncpg.Connection, account_id: UUID) -> None:
    """Delete an account; its transactions and their splits cascade away with it."""
    deleted = await connection.execute("DELETE FROM account WHERE id = $1", account_id)
    if deleted == "DELETE 0":
        raise NotFound("account", account_id)
