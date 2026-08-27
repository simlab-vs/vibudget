"""Payee endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.repositories import payees as repository
from vibudget.schemas import Payee, PayeeCreate, PayeeUpdate

router = APIRouter(prefix="/payees", tags=["payees"])


@router.get("")
async def list_payees(
    connection: ConnectionDep,
    search: Annotated[str | None, Query(description="Case-insensitive name filter")] = None,
) -> list[Payee]:
    return await repository.list_payees(connection, search=search)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payee(payload: PayeeCreate, connection: ConnectionDep) -> Payee:
    return await repository.create_payee(connection, payload)


@router.get("/{payee_id}")
async def get_payee(payee_id: UUID, connection: ConnectionDep) -> Payee:
    return await repository.get_payee(connection, payee_id)


@router.patch("/{payee_id}")
async def update_payee(
    payee_id: UUID, payload: PayeeUpdate, connection: ConnectionDep
) -> Payee:
    return await repository.update_payee(connection, payee_id, payload)


@router.delete("/{payee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payee(payee_id: UUID, connection: ConnectionDep) -> None:
    await repository.delete_payee(connection, payee_id)
