"""Payees: who money is paid to or received from."""

from vibudget.schemas.common import Name, Record, Schema


class PayeeCreate(Schema):
    name: Name


class PayeeUpdate(Schema):
    name: Name | None = None


class Payee(Record):
    name: Name
