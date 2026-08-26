"""Building blocks shared by every schema module."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Memo = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]

Milliunits = Annotated[
    int, Field(description="Signed amount in milliunits; 1 unit = 1000 milliunits")
]

MILLIUNITS_PER_UNIT = 1000


def to_milliunits(amount: float | int) -> int:
    """Convert a decimal currency amount to the integer milliunits we store."""
    return round(amount * MILLIUNITS_PER_UNIT)


def from_milliunits(milliunits: int) -> float:
    """Convert stored milliunits back to a decimal currency amount."""
    return milliunits / MILLIUNITS_PER_UNIT


class Schema(BaseModel):
    """Base for payloads coming in over the API."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Record(Schema):
    """Base for rows coming out of the database."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
