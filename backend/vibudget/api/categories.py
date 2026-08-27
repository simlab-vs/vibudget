"""Category endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.repositories import categories as repository
from vibudget.schemas import Category, CategoryCreate, CategoryGroup, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    connection: ConnectionDep,
    include_hidden: Annotated[bool, Query()] = False,
) -> list[CategoryGroup]:
    """The two-level tree: every group with the sub-categories it owns."""
    return await repository.list_categories(connection, include_hidden=include_hidden)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, connection: ConnectionDep) -> Category:
    return await repository.create_category(connection, payload)


@router.get("/{category_id}")
async def get_category(category_id: UUID, connection: ConnectionDep) -> Category:
    return await repository.get_category(connection, category_id)


@router.patch("/{category_id}")
async def update_category(
    category_id: UUID, payload: CategoryUpdate, connection: ConnectionDep
) -> Category:
    return await repository.update_category(connection, category_id, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, connection: ConnectionDep) -> None:
    await repository.delete_category(connection, category_id)
