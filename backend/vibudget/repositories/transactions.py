"""Transaction rows together with the splits that make them up.

A transaction always carries at least one split and the splits always sum to
its amount, which the pydantic payloads guarantee on the way in. Writing both
tables under one database transaction keeps that true on the way out.
"""

from collections import defaultdict
from datetime import date as Date
from uuid import UUID

import asyncpg

from vibudget.api.errors import Conflict, InvalidReference, NotFound
from vibudget.repositories.common import assignments, translate_writes
from vibudget.schemas import (
    Split,
    SplitCreate,
    Transaction,
    TransactionCreate,
    TransactionUpdate,
)

SPLIT_COLUMNS = "id, category_id, amount, memo"


async def list_transactions(
    connection: asyncpg.Connection,
    *,
    account_id: UUID | None = None,
    payee_id: UUID | None = None,
    category_id: UUID | None = None,
    since: Date | None = None,
    until: Date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Transaction]:
    rows = await connection.fetch(
        "SELECT * FROM transaction"
        " WHERE ($1::uuid IS NULL OR account_id = $1)"
        "   AND ($2::uuid IS NULL OR payee_id = $2)"
        "   AND ($3::uuid IS NULL OR EXISTS ("
        "         SELECT 1 FROM transaction_split"
        "         WHERE transaction_id = transaction.id AND category_id = $3))"
        "   AND ($4::date IS NULL OR date >= $4)"
        "   AND ($5::date IS NULL OR date <= $5)"
        " ORDER BY date DESC, created_at DESC"
        " LIMIT $6 OFFSET $7",
        account_id,
        payee_id,
        category_id,
        since,
        until,
        limit,
        offset,
    )

    splits = await _splits_by_transaction(connection, [row["id"] for row in rows])
    return [Transaction(**row, splits=splits[row["id"]]) for row in rows]


async def get_transaction(
    connection: asyncpg.Connection, transaction_id: UUID
) -> Transaction:
    row = await connection.fetchrow(
        "SELECT * FROM transaction WHERE id = $1", transaction_id
    )
    if row is None:
        raise NotFound("transaction", transaction_id)
    splits = await connection.fetch(
        f"SELECT {SPLIT_COLUMNS} FROM transaction_split"
        " WHERE transaction_id = $1 ORDER BY id",
        transaction_id,
    )
    return Transaction(**row, splits=[Split(**split) for split in splits])


async def create_transaction(
    connection: asyncpg.Connection, payload: TransactionCreate
) -> Transaction:
    async with connection.transaction():
        await _reject_unassignable(connection, payload.splits)
        with translate_writes("transaction"):
            row = await connection.fetchrow(
                "INSERT INTO transaction (account_id, payee_id, date, amount, memo, cleared)"
                " VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
                payload.account_id,
                payload.payee_id,
                payload.date,
                payload.amount,
                payload.memo,
                payload.cleared.value,
            )
            splits = await _insert_splits(connection, row["id"], payload.splits)
    return Transaction(**row, splits=splits)


async def update_transaction(
    connection: asyncpg.Connection, transaction_id: UUID, payload: TransactionUpdate
) -> Transaction:
    """Apply a partial update, replacing the splits wholesale when they are given.

    The payload validator already refuses splits that do not sum to the amount
    they arrive with. Changing the amount on its own is only meaningful for a
    single-category transaction, whose one split follows the new amount; a
    split transaction has to say how the new amount divides up.
    """
    values = payload.model_dump(exclude_unset=True)
    values.pop("splits", None)

    async with connection.transaction():
        current = await get_transaction(connection, transaction_id)

        if values:
            clause, arguments = assignments(values)
            with translate_writes("transaction"):
                await connection.execute(
                    f"UPDATE transaction SET {clause} WHERE id = ${len(arguments) + 1}",
                    *arguments,
                    transaction_id,
                )

        if payload.splits is not None:
            await _reject_unassignable(connection, payload.splits)
            await connection.execute(
                "DELETE FROM transaction_split WHERE transaction_id = $1", transaction_id
            )
            with translate_writes("transaction"):
                await _insert_splits(connection, transaction_id, payload.splits)
        elif payload.amount is not None and payload.amount != current.amount:
            if len(current.splits) > 1:
                raise Conflict(
                    "the amount of a split transaction can only be changed by sending"
                    " the splits it divides into"
                )
            await connection.execute(
                "UPDATE transaction_split SET amount = $1 WHERE transaction_id = $2",
                payload.amount,
                transaction_id,
            )

        return await get_transaction(connection, transaction_id)


async def delete_transaction(
    connection: asyncpg.Connection, transaction_id: UUID
) -> None:
    """Delete a transaction; its splits cascade away with it."""
    deleted = await connection.execute(
        "DELETE FROM transaction WHERE id = $1", transaction_id
    )
    if deleted == "DELETE 0":
        raise NotFound("transaction", transaction_id)


async def _splits_by_transaction(
    connection: asyncpg.Connection, transaction_ids: list[UUID]
) -> dict[UUID, list[Split]]:
    """Fetch the splits of a page of transactions in one round trip."""
    splits: dict[UUID, list[Split]] = defaultdict(list)
    if not transaction_ids:
        return splits

    rows = await connection.fetch(
        f"SELECT transaction_id, {SPLIT_COLUMNS} FROM transaction_split"
        " WHERE transaction_id = ANY($1::uuid[]) ORDER BY id",
        transaction_ids,
    )
    for row in rows:
        fields = dict(row)
        splits[fields.pop("transaction_id")].append(Split(**fields))
    return splits


async def _insert_splits(
    connection: asyncpg.Connection, transaction_id: UUID, splits: list[SplitCreate]
) -> list[Split]:
    rows = [
        await connection.fetchrow(
            "INSERT INTO transaction_split (transaction_id, category_id, amount, memo)"
            f" VALUES ($1, $2, $3, $4) RETURNING {SPLIT_COLUMNS}",
            transaction_id,
            split.category_id,
            split.amount,
            split.memo,
        )
        for split in splits
    ]
    return [Split(**row) for row in rows]


async def _reject_unassignable(
    connection: asyncpg.Connection, splits: list[SplitCreate]
) -> None:
    """Only sub-categories may be assigned; a group is not a place to spend."""
    category_ids = {split.category_id for split in splits}
    rows = await connection.fetch(
        "SELECT id, parent_id FROM category WHERE id = ANY($1::uuid[])",
        list(category_ids),
    )
    parents = {row["id"]: row["parent_id"] for row in rows}

    for category_id in category_ids:
        if category_id not in parents:
            raise InvalidReference(f"category {category_id} does not exist")
        if parents[category_id] is None:
            raise Conflict(
                f"category {category_id} is a group; only sub-categories can be assigned"
            )
