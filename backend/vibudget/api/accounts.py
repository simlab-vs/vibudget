"""Account endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.repositories import accounts as repository
from vibudget.schemas import Account, AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(
    connection: ConnectionDep,
    include_closed: Annotated[bool, Query()] = False,
) -> list[Account]:
    return await repository.list_accounts(connection, include_closed=include_closed)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, connection: ConnectionDep) -> Account:
    return await repository.create_account(connection, payload)


@router.get("/{account_id}")
async def get_account(account_id: UUID, connection: ConnectionDep) -> Account:
    return await repository.get_account(connection, account_id)


@router.patch("/{account_id}")
async def update_account(
    account_id: UUID, payload: AccountUpdate, connection: ConnectionDep
) -> Account:
    return await repository.update_account(connection, account_id, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: UUID, connection: ConnectionDep) -> None:
    await repository.delete_account(connection, account_id)
