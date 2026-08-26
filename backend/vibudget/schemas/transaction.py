"""Transactions: money moving in or out of one account.

Every transaction carries at least one split. The common single-category case
is a transaction with exactly one split covering the full amount; a split
transaction has several. Split amounts always sum to the transaction amount.
"""

from datetime import date as Date
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from vibudget.schemas.common import Memo, Milliunits, Record, Schema


class ClearedStatus(StrEnum):
    UNCLEARED = "uncleared"
    CLEARED = "cleared"
    RECONCILED = "reconciled"


class SplitCreate(Schema):
    category_id: UUID
    amount: Milliunits
    memo: Memo | None = None


class Split(Schema):
    id: UUID
    category_id: UUID
    amount: Milliunits
    memo: Memo | None = None


class TransactionCreate(Schema):
    account_id: UUID
    date: Date
    amount: Milliunits
    payee_id: UUID | None = None
    memo: Memo | None = None
    cleared: ClearedStatus = ClearedStatus.UNCLEARED
    splits: list[SplitCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def splits_sum_to_amount(self) -> Self:
        total = sum(split.amount for split in self.splits)
        if total != self.amount:
            raise ValueError(
                f"splits sum to {total} milliunits but the transaction is {self.amount}"
            )
        return self


class TransactionUpdate(Schema):
    account_id: UUID | None = None
    date: Date | None = None
    amount: Milliunits | None = None
    payee_id: UUID | None = None
    memo: Memo | None = None
    cleared: ClearedStatus | None = None
    splits: list[SplitCreate] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def splits_sum_to_amount(self) -> Self:
        if self.splits is None:
            return self
        if self.amount is None:
            raise ValueError("amount must be given alongside splits so the two can be checked")
        total = sum(split.amount for split in self.splits)
        if total != self.amount:
            raise ValueError(
                f"splits sum to {total} milliunits but the transaction is {self.amount}"
            )
        return self


class Transaction(Record):
    account_id: UUID
    date: Date
    amount: Milliunits
    payee_id: UUID | None = None
    memo: Memo | None = None
    cleared: ClearedStatus
    splits: list[Split] = Field(default_factory=list)

    @property
    def is_split(self) -> bool:
        return len(self.splits) > 1
