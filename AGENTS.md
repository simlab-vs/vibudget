# ViBudget

A YNAB clone that features a subset of features:
- Creating and managing accounts (cash and credit);
- Creating and managing categories and sub-categories;
- Creating and managing payees;
- Creating and managing transactions that associated 
  with one account, one or more category, and one payee.

## Architecture

The application is a fairly classical back- and front-end architecture. 
We use FastAPI as backend and Astro as frontend framework (server-side
generation), with a PostgreSQL database.

To define data schemas manipulated in memory and in the database, use 
the modern stack pydantic + asyncpg. Do NOT introduce use sqlalchemy
to avoid duplicates.

FastAPI replaced the originally planned Flask: it is ASGI-native, so the
asyncpg pool is created once in the lifespan hook on the same loop the
whole app runs on, and the pydantic schemas double as request validation,
response serialisation and the OpenAPI contract.

## Conventions

Amounts are stored and passed around as signed integer milliunits
(1 unit = 1000 milliunits); outflows negative, inflows positive. No
monetary value is ever represented as a float.

The database schema lives in numbered plain-SQL files under
backend/vibudget/migrations/ and is the source of truth that the
pydantic schemas in backend/vibudget/schemas/ mirror. Each entity has
three shapes: XCreate for writes, XUpdate for partial writes, and X for
a row read back.

Categories form a two-level tree: no parent means a group, a parent
means a sub-category. Only sub-categories are assignable to a
transaction split.
