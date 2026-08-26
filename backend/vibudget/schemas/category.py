"""Categories: a two-level tree of budget groups and their sub-categories.

A category with ``parent_id`` unset is a group; one with a parent set is a
sub-category. Only sub-categories may be assigned to a transaction split.
"""

from uuid import UUID

from pydantic import Field

from vibudget.schemas.common import Memo, Name, Record, Schema


class CategoryCreate(Schema):
    name: Name
    parent_id: UUID | None = None
    note: Memo | None = None


class CategoryUpdate(Schema):
    name: Name | None = None
    parent_id: UUID | None = None
    hidden: bool | None = None
    note: Memo | None = None


class Category(Record):
    name: Name
    parent_id: UUID | None = None
    hidden: bool
    note: Memo | None = None

    @property
    def is_group(self) -> bool:
        return self.parent_id is None


class CategoryGroup(Category):
    """A top-level category together with the sub-categories it owns."""

    children: list[Category] = Field(default_factory=list)
