from uuid import uuid4

import pytest
from pydantic import ValidationError

from vibudget.schemas import (
    AccountCreate,
    AccountType,
    CategoryCreate,
    SplitCreate,
    TransactionCreate,
    from_milliunits,
    to_milliunits,
)


def test_milliunits_round_trip():
    assert to_milliunits(12.34) == 12340
    assert from_milliunits(12340) == 12.34


def test_account_name_is_stripped_and_required():
    assert AccountCreate(name="  Checking  ", type=AccountType.CASH).name == "Checking"
    with pytest.raises(ValidationError):
        AccountCreate(name="   ", type=AccountType.CASH)


def test_account_rejects_unknown_type():
    with pytest.raises(ValidationError):
        AccountCreate(name="Savings", type="crypto")


def test_category_defaults_to_a_group():
    assert CategoryCreate(name="Everyday Expenses").parent_id is None


def test_transaction_requires_splits_summing_to_amount():
    account_id, category_id = uuid4(), uuid4()
    transaction = TransactionCreate(
        account_id=account_id,
        date="2026-08-26",
        amount=-4500,
        splits=[SplitCreate(category_id=category_id, amount=-4500)],
    )
    assert transaction.splits[0].amount == transaction.amount

    with pytest.raises(ValidationError, match="splits sum to"):
        TransactionCreate(
            account_id=account_id,
            date="2026-08-26",
            amount=-4500,
            splits=[SplitCreate(category_id=category_id, amount=-1000)],
        )


def test_transaction_requires_at_least_one_split():
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=uuid4(), date="2026-08-26", amount=0, splits=[]
        )


def test_split_transaction_sums_across_categories():
    transaction = TransactionCreate(
        account_id=uuid4(),
        date="2026-08-26",
        amount=-10_000,
        splits=[
            SplitCreate(category_id=uuid4(), amount=-6_000, memo="groceries"),
            SplitCreate(category_id=uuid4(), amount=-4_000, memo="household"),
        ],
    )
    assert sum(split.amount for split in transaction.splits) == transaction.amount
