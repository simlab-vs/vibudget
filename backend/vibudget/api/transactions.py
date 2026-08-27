"""Transaction endpoints."""

from datetime import date as Date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.repositories import transactions as repository
from vibudget.schemas import Transaction, TransactionCreate, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
async def list_transactions(
    connection: ConnectionDep,
    account_id: Annotated[UUID | None, Query()] = None,
    payee_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    since: Annotated[Date | None, Query(description="Inclusive lower bound on date")] = None,
    until: Annotated[Date | None, Query(description="Inclusive upper bound on date")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Transaction]:
    return await repository.list_transactions(
        connection,
        account_id=account_id,
        payee_id=payee_id,
        category_id=category_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate, connection: ConnectionDep
) -> Transaction:
    return await repository.create_transaction(connection, payload)


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: UUID, connection: ConnectionDep) -> Transaction:
    return await repository.get_transaction(connection, transaction_id)


@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: UUID, payload: TransactionUpdate, connection: ConnectionDep
) -> Transaction:
    return await repository.update_transaction(connection, transaction_id, payload)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: UUID, connection: ConnectionDep) -> None:
    await repository.delete_transaction(connection, transaction_id)
