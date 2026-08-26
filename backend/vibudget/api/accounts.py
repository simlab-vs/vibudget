"""Account endpoints. Bodies land with the repository layer."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.schemas import Account, AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(
    connection: ConnectionDep,
    include_closed: Annotated[bool, Query()] = False,
) -> list[Account]:
    raise NotImplementedError


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, connection: ConnectionDep) -> Account:
    raise NotImplementedError


@router.get("/{account_id}")
async def get_account(account_id: UUID, connection: ConnectionDep) -> Account:
    raise NotImplementedError


@router.patch("/{account_id}")
async def update_account(
    account_id: UUID, payload: AccountUpdate, connection: ConnectionDep
) -> Account:
    raise NotImplementedError


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: UUID, connection: ConnectionDep) -> None:
    raise NotImplementedError
