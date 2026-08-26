"""Category endpoints. Bodies land with the repository layer."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from vibudget.db import ConnectionDep
from vibudget.schemas import Category, CategoryCreate, CategoryGroup, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    connection: ConnectionDep,
    include_hidden: Annotated[bool, Query()] = False,
) -> list[CategoryGroup]:
    """The two-level tree: every group with the sub-categories it owns."""
    raise NotImplementedError


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, connection: ConnectionDep) -> Category:
    raise NotImplementedError


@router.get("/{category_id}")
async def get_category(category_id: UUID, connection: ConnectionDep) -> Category:
    raise NotImplementedError


@router.patch("/{category_id}")
async def update_category(
    category_id: UUID, payload: CategoryUpdate, connection: ConnectionDep
) -> Category:
    raise NotImplementedError


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, connection: ConnectionDep) -> None:
    raise NotImplementedError
