"""Endpoint tests: every route the UI screens call, against real SQL."""

from httpx import AsyncClient

UNKNOWN = "00000000-0000-0000-0000-000000000001"


async def create(client: AsyncClient, path: str, **body) -> dict:
    response = await client.post(f"/api/{path}", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def budget(client: AsyncClient) -> dict[str, dict]:
    """A small budget: two accounts, a two-level tree, a payee."""
    group = await create(client, "categories", name="Everyday Expenses")
    return {
        "checking": await create(client, "accounts", name="Checking", type="cash"),
        "card": await create(client, "accounts", name="Visa", type="credit"),
        "group": group,
        "groceries": await create(client, "categories", name="Groceries", parent_id=group["id"]),
        "dining": await create(client, "categories", name="Dining Out", parent_id=group["id"]),
        "payee": await create(client, "payees", name="Migros"),
    }


async def test_account_round_trip(client: AsyncClient):
    account = await create(client, "accounts", name="  Checking  ", type="cash", note="main")
    assert account["name"] == "Checking"
    assert account["balance"] == 0
    assert account["closed"] is False

    fetched = await client.get(f"/api/accounts/{account['id']}")
    assert fetched.json() == account

    renamed = await client.patch(f"/api/accounts/{account['id']}", json={"name": "Everyday"})
    assert renamed.json()["name"] == "Everyday"
    assert renamed.json()["note"] == "main", "an unset field is left alone"

    cleared = await client.patch(f"/api/accounts/{account['id']}", json={"note": None})
    assert cleared.json()["note"] is None, "an explicit null clears the field"

    assert (await client.delete(f"/api/accounts/{account['id']}")).status_code == 204
    assert (await client.get(f"/api/accounts/{account['id']}")).status_code == 404


async def test_account_names_are_unique_case_insensitively(client: AsyncClient):
    await create(client, "accounts", name="Checking", type="cash")
    response = await client.post("/api/accounts", json={"name": "checking", "type": "cash"})
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


async def test_closed_accounts_are_listed_on_request_only(client: AsyncClient):
    account = await create(client, "accounts", name="Old Savings", type="cash")
    await client.patch(f"/api/accounts/{account['id']}", json={"closed": True})

    assert (await client.get("/api/accounts")).json() == []
    assert len((await client.get("/api/accounts?include_closed=true")).json()) == 1


async def test_categories_come_back_as_a_two_level_tree(client: AsyncClient):
    data = await budget(client)
    await create(client, "categories", name="Rent")

    tree = (await client.get("/api/categories")).json()
    assert [group["name"] for group in tree] == ["Everyday Expenses", "Rent"]
    assert [child["name"] for child in tree[0]["children"]] == ["Dining Out", "Groceries"]
    assert tree[1]["children"] == []
    assert tree[0]["id"] == data["group"]["id"]


async def test_category_nesting_stops_at_two_levels(client: AsyncClient):
    data = await budget(client)
    response = await client.post(
        "/api/categories", json={"name": "Too Deep", "parent_id": data["groceries"]["id"]}
    )
    assert response.status_code == 409


async def test_category_parent_must_exist(client: AsyncClient):
    response = await client.post("/api/categories", json={"name": "Orphan", "parent_id": UNKNOWN})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_reference"


async def test_hidden_categories_are_filtered_with_their_children(client: AsyncClient):
    data = await budget(client)
    await client.patch(f"/api/categories/{data['dining']['id']}", json={"hidden": True})

    assert [c["name"] for c in (await client.get("/api/categories")).json()[0]["children"]] == [
        "Groceries"
    ]

    await client.patch(f"/api/categories/{data['group']['id']}", json={"hidden": True})
    assert (await client.get("/api/categories")).json() == []
    assert len((await client.get("/api/categories?include_hidden=true")).json()) == 1


async def test_category_in_use_cannot_be_deleted(client: AsyncClient):
    data = await budget(client)
    assert (await client.delete(f"/api/categories/{data['group']['id']}")).status_code == 409
    assert (await client.delete(f"/api/categories/{data['groceries']['id']}")).status_code == 204


async def test_payees_are_searched_case_insensitively(client: AsyncClient):
    await create(client, "payees", name="Migros")
    await create(client, "payees", name="Coop")

    assert [p["name"] for p in (await client.get("/api/payees")).json()] == ["Coop", "Migros"]
    assert [p["name"] for p in (await client.get("/api/payees?search=MIG")).json()] == ["Migros"]


async def test_payee_named_by_a_transaction_cannot_be_deleted(client: AsyncClient):
    data = await budget(client)
    await create(
        client,
        "transactions",
        account_id=data["checking"]["id"],
        payee_id=data["payee"]["id"],
        date="2026-08-20",
        amount=-45500,
        splits=[{"category_id": data["groceries"]["id"], "amount": -45500}],
    )
    assert (await client.delete(f"/api/payees/{data['payee']['id']}")).status_code == 409


async def test_transaction_round_trip_with_splits(client: AsyncClient):
    data = await budget(client)
    transaction = await create(
        client,
        "transactions",
        account_id=data["card"]["id"],
        payee_id=data["payee"]["id"],
        date="2026-08-22",
        amount=-80000,
        cleared="cleared",
        splits=[
            {"category_id": data["groceries"]["id"], "amount": -50000, "memo": "food"},
            {"category_id": data["dining"]["id"], "amount": -30000},
        ],
    )
    assert sum(split["amount"] for split in transaction["splits"]) == -80000

    fetched = (await client.get(f"/api/transactions/{transaction['id']}")).json()
    assert {split["memo"] for split in fetched["splits"]} == {"food", None}
    assert fetched["cleared"] == "cleared"


async def test_transactions_are_listed_newest_first_and_filtered(client: AsyncClient):
    data = await budget(client)
    for date, account, category in (
        ("2026-08-20", "checking", "groceries"),
        ("2026-08-22", "card", "dining"),
        ("2026-08-25", "checking", "groceries"),
    ):
        await create(
            client,
            "transactions",
            account_id=data[account]["id"],
            payee_id=data["payee"]["id"],
            date=date,
            amount=-1000,
            splits=[{"category_id": data[category]["id"], "amount": -1000}],
        )

    listed = (await client.get("/api/transactions")).json()
    assert [t["date"] for t in listed] == ["2026-08-25", "2026-08-22", "2026-08-20"]

    async def count(query: str) -> int:
        return len((await client.get(f"/api/transactions?{query}")).json())

    assert await count(f"account_id={data['checking']['id']}") == 2
    assert await count(f"category_id={data['dining']['id']}") == 1
    assert await count(f"payee_id={data['payee']['id']}") == 3
    assert await count("since=2026-08-22") == 2
    assert await count("since=2026-08-21&until=2026-08-24") == 1
    assert await count("limit=2") == 2
    assert await count("limit=2&offset=2") == 1


async def test_account_balance_sums_its_transactions(client: AsyncClient):
    data = await budget(client)
    for amount in (-45500, 500000):
        await create(
            client,
            "transactions",
            account_id=data["checking"]["id"],
            date="2026-08-20",
            amount=amount,
            splits=[{"category_id": data["groceries"]["id"], "amount": amount}],
        )

    account = (await client.get(f"/api/accounts/{data['checking']['id']}")).json()
    assert account["balance"] == 454500

    patched = await client.patch(
        f"/api/accounts/{data['checking']['id']}", json={"name": "Main"}
    )
    assert patched.json()["balance"] == 454500, "a write reads the balance back too"


async def test_splits_must_sum_to_the_amount(client: AsyncClient):
    data = await budget(client)
    response = await client.post(
        "/api/transactions",
        json={
            "account_id": data["checking"]["id"],
            "date": "2026-08-20",
            "amount": -1000,
            "splits": [{"category_id": data["groceries"]["id"], "amount": -900}],
        },
    )
    assert response.status_code == 422


async def test_a_split_must_name_a_sub_category(client: AsyncClient):
    data = await budget(client)
    response = await client.post(
        "/api/transactions",
        json={
            "account_id": data["checking"]["id"],
            "date": "2026-08-20",
            "amount": -1000,
            "splits": [{"category_id": data["group"]["id"], "amount": -1000}],
        },
    )
    assert response.status_code == 409
    assert "sub-categories" in response.json()["message"]


async def test_a_transaction_needs_an_account_that_exists(client: AsyncClient):
    data = await budget(client)
    response = await client.post(
        "/api/transactions",
        json={
            "account_id": UNKNOWN,
            "date": "2026-08-20",
            "amount": -1000,
            "splits": [{"category_id": data["groceries"]["id"], "amount": -1000}],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_reference"


async def test_changing_the_amount_carries_a_single_split_along(client: AsyncClient):
    data = await budget(client)
    transaction = await create(
        client,
        "transactions",
        account_id=data["checking"]["id"],
        date="2026-08-20",
        amount=-45500,
        splits=[{"category_id": data["groceries"]["id"], "amount": -45500}],
    )

    updated = await client.patch(
        f"/api/transactions/{transaction['id']}", json={"amount": -50000}
    )
    assert [split["amount"] for split in updated.json()["splits"]] == [-50000]


async def test_a_split_transaction_needs_its_splits_to_change_amount(client: AsyncClient):
    data = await budget(client)
    transaction = await create(
        client,
        "transactions",
        account_id=data["checking"]["id"],
        date="2026-08-20",
        amount=-80000,
        splits=[
            {"category_id": data["groceries"]["id"], "amount": -50000},
            {"category_id": data["dining"]["id"], "amount": -30000},
        ],
    )

    refused = await client.patch(
        f"/api/transactions/{transaction['id']}", json={"amount": -90000}
    )
    assert refused.status_code == 409

    accepted = await client.patch(
        f"/api/transactions/{transaction['id']}",
        json={
            "amount": -90000,
            "splits": [
                {"category_id": data["groceries"]["id"], "amount": -60000},
                {"category_id": data["dining"]["id"], "amount": -30000},
            ],
        },
    )
    assert accepted.status_code == 200
    assert sum(split["amount"] for split in accepted.json()["splits"]) == -90000

    account = (await client.get(f"/api/accounts/{data['checking']['id']}")).json()
    assert account["balance"] == -90000


async def test_deleting_an_account_takes_its_transactions_with_it(client: AsyncClient):
    data = await budget(client)
    await create(
        client,
        "transactions",
        account_id=data["checking"]["id"],
        date="2026-08-20",
        amount=-1000,
        splits=[{"category_id": data["groceries"]["id"], "amount": -1000}],
    )

    assert (await client.delete(f"/api/accounts/{data['checking']['id']}")).status_code == 204
    assert (await client.get("/api/transactions")).json() == []


async def test_missing_rows_answer_404(client: AsyncClient):
    for path in ("accounts", "categories", "payees", "transactions"):
        assert (await client.get(f"/api/{path}/{UNKNOWN}")).status_code == 404
        assert (await client.delete(f"/api/{path}/{UNKNOWN}")).status_code == 404
        assert (await client.patch(f"/api/{path}/{UNKNOWN}", json={})).status_code == 404
