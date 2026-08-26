"""Payee endpoints. Bodies land with the repository layer."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.schemas import Payee, PayeeCreate, PayeeUpdate

router = APIRouter(prefix="/payees", tags=["payees"])


@router.get("")
async def list_payees(
    connection: ConnectionDep,
    search: Annotated[str | None, Query(description="Case-insensitive name filter")] = None,
) -> list[Payee]:
    raise NotImplementedError


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payee(payload: PayeeCreate, connection: ConnectionDep) -> Payee:
    raise NotImplementedError


@router.get("/{payee_id}")
async def get_payee(payee_id: UUID, connection: ConnectionDep) -> Payee:
    raise NotImplementedError


@router.patch("/{payee_id}")
async def update_payee(
    payee_id: UUID, payload: PayeeUpdate, connection: ConnectionDep
) -> Payee:
    raise NotImplementedError


@router.delete("/{payee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payee(payee_id: UUID, connection: ConnectionDep) -> None:
    raise NotImplementedError
