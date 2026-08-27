"""Category rows and the two-level tree the budget screen renders.

A row with no ``parent_id`` is a group; one with a parent is a sub-category.
The depth guard in the migration keeps that tree exactly two levels deep.
"""

from uuid import UUID

import asyncpg

from vibudget.api.errors import NotFound
from vibudget.repositories.common import assignments, translate_delete, translate_writes
from vibudget.schemas import Category, CategoryCreate, CategoryGroup, CategoryUpdate


async def list_categories(
    connection: asyncpg.Connection, *, include_hidden: bool = False
) -> list[CategoryGroup]:
    """Every group with the sub-categories it owns, both ordered by name.

    A sub-category whose group is filtered out goes with it: the tree only
    ever contains children reachable from a group in the same response.
    """
    rows = await connection.fetch(
        "SELECT * FROM category"
        " WHERE ($1 OR NOT hidden)"
        " ORDER BY parent_id IS NOT NULL, lower(name)",
        include_hidden,
    )

    groups: dict[UUID, CategoryGroup] = {}
    for row in rows:
        if row["parent_id"] is None:
            groups[row["id"]] = CategoryGroup(**row)
        elif row["parent_id"] in groups:
            groups[row["parent_id"]].children.append(Category(**row))
    return list(groups.values())


async def get_category(connection: asyncpg.Connection, category_id: UUID) -> Category:
    row = await connection.fetchrow("SELECT * FROM category WHERE id = $1", category_id)
    if row is None:
        raise NotFound("category", category_id)
    return Category(**row)


async def create_category(
    connection: asyncpg.Connection, payload: CategoryCreate
) -> Category:
    with translate_writes("category"):
        row = await connection.fetchrow(
            "INSERT INTO category (name, parent_id, note) VALUES ($1, $2, $3) RETURNING *",
            payload.name,
            payload.parent_id,
            payload.note,
        )
    return Category(**row)


async def update_category(
    connection: asyncpg.Connection, category_id: UUID, payload: CategoryUpdate
) -> Category:
    clause, values = assignments(payload.model_dump(exclude_unset=True))
    if not clause:
        return await get_category(connection, category_id)

    with translate_writes("category"):
        row = await connection.fetchrow(
            f"UPDATE category SET {clause} WHERE id = ${len(values) + 1} RETURNING *",
            *values,
            category_id,
        )
    if row is None:
        raise NotFound("category", category_id)
    return Category(**row)


async def delete_category(connection: asyncpg.Connection, category_id: UUID) -> None:
    with translate_delete("the category still has sub-categories or transaction splits"):
        deleted = await connection.execute("DELETE FROM category WHERE id = $1", category_id)
    if deleted == "DELETE 0":
        raise NotFound("category", category_id)
