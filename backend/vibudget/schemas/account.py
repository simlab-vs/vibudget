"""Accounts: where money physically sits."""

from enum import StrEnum

from pydantic import Field

from vibudget.schemas.common import Memo, Milliunits, Name, Record, Schema


class AccountType(StrEnum):
    CASH = "cash"
    CREDIT = "credit"


class AccountCreate(Schema):
    name: Name
    type: AccountType
    on_budget: bool = True
    note: Memo | None = None


class AccountUpdate(Schema):
    name: Name | None = None
    type: AccountType | None = None
    on_budget: bool | None = None
    closed: bool | None = None
    note: Memo | None = None


class Account(Record):
    name: Name
    type: AccountType
    on_budget: bool
    closed: bool
    note: Memo | None = None
    balance: Milliunits = Field(default=0, description="Sum of the account's transactions")
