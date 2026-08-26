"""HTTP layer: one router per entity, all mounted under /api."""

from fastapi import APIRouter

from vibudget.api.accounts import router as accounts
from vibudget.api.categories import router as categories
from vibudget.api.payees import router as payees
from vibudget.api.transactions import router as transactions

api = APIRouter(prefix="/api")

for router in (accounts, categories, payees, transactions):
    api.include_router(router)

__all__ = ["api"]
