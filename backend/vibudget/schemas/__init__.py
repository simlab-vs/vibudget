"""Pydantic schemas mirroring the tables in ``migrations/001_initial.sql``.

Each entity has three shapes: ``XCreate`` for writes, ``XUpdate`` for partial
writes, and ``X`` for a row read back from the database.
"""

from vibudget.schemas.account import Account, AccountCreate, AccountType, AccountUpdate
from vibudget.schemas.category import Category, CategoryCreate, CategoryGroup, CategoryUpdate
from vibudget.schemas.common import (
    MILLIUNITS_PER_UNIT,
    Memo,
    Milliunits,
    Name,
    Record,
    Schema,
    from_milliunits,
    to_milliunits,
)
from vibudget.schemas.payee import Payee, PayeeCreate, PayeeUpdate
from vibudget.schemas.transaction import (
    ClearedStatus,
    Split,
    SplitCreate,
    Transaction,
    TransactionCreate,
    TransactionUpdate,
)

__all__ = [
    "MILLIUNITS_PER_UNIT",
    "Account",
    "AccountCreate",
    "AccountType",
    "AccountUpdate",
    "Category",
    "CategoryCreate",
    "CategoryGroup",
    "CategoryUpdate",
    "ClearedStatus",
    "Memo",
    "Milliunits",
    "Name",
    "Payee",
    "PayeeCreate",
    "PayeeUpdate",
    "Record",
    "Schema",
    "Split",
    "SplitCreate",
    "Transaction",
    "TransactionCreate",
    "TransactionUpdate",
    "from_milliunits",
    "to_milliunits",
]
