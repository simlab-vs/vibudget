"""Repository layer: the SQL behind the endpoints, one module per entity.

Each module exposes plain async functions taking the request's connection as
their first argument, so an endpoint reads as one call and the SQL stays in
one place.
"""

from vibudget.repositories import accounts, categories, payees, transactions

__all__ = ["accounts", "categories", "payees", "transactions"]
