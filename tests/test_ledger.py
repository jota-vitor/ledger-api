from tests.conftest import key


def balance(client, account_id: int) -> int:
    return client.get(f"/accounts/{account_id}").json()["balance_cents"]


def transfer(client, from_id, to_id, amount, headers=None):
    return client.post(
        "/transfers",
        json={"from_account_id": from_id, "to_account_id": to_id, "amount_cents": amount},
        headers=headers or key(),
    )


def test_new_account_starts_at_zero(client, new_account):
    account = client.get(f"/accounts/{new_account()}").json()
    assert account["balance_cents"] == 0
    assert account["balance"] == "R$ 0,00"


def test_deposit_and_transfer_move_money(client, new_account):
    ana = new_account("Ana", 10_000)
    bia = new_account("Bia")

    response = transfer(client, ana, bia, 2_590)

    assert response.status_code == 201
    assert balance(client, ana) == 7_410
    assert balance(client, bia) == 2_590


def test_insufficient_funds(client, new_account):
    ana = new_account("Ana", 1_000)
    bia = new_account("Bia")

    response = transfer(client, ana, bia, 1_001)

    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_funds"
    assert balance(client, ana) == 1_000


def test_transfer_to_same_account(client, new_account):
    ana = new_account("Ana", 1_000)
    response = transfer(client, ana, ana, 100)
    assert response.json()["code"] == "same_account"


def test_unknown_account(client, new_account):
    ana = new_account("Ana", 1_000)
    response = transfer(client, ana, 9999, 100)
    assert response.status_code == 404


def test_missing_idempotency_key_is_rejected(client, new_account):
    ana = new_account("Ana", 1_000)
    bia = new_account("Bia")
    response = client.post(
        "/transfers", json={"from_account_id": ana, "to_account_id": bia, "amount_cents": 1}
    )
    assert response.status_code == 422


def test_retry_with_same_key_does_not_charge_twice(client, new_account):
    ana = new_account("Ana", 10_000)
    bia = new_account("Bia")
    headers = key()

    first = transfer(client, ana, bia, 3_000, headers)
    second = transfer(client, ana, bia, 3_000, headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["Idempotent-Replayed"] == "true"
    assert second.json()["id"] == first.json()["id"]
    assert balance(client, ana) == 7_000


def test_same_key_with_different_payload_conflicts(client, new_account):
    ana = new_account("Ana", 10_000)
    bia = new_account("Bia")
    headers = key()

    transfer(client, ana, bia, 3_000, headers)
    response = transfer(client, ana, bia, 4_000, headers)

    assert response.status_code == 409
    assert balance(client, ana) == 7_000


def test_statement_shows_entries_newest_first(client, new_account):
    ana = new_account("Ana", 10_000)
    bia = new_account("Bia")
    transfer(client, ana, bia, 1_500)

    page = client.get(f"/accounts/{ana}/statement").json()

    assert page["total"] == 2
    assert [e["amount_cents"] for e in page["items"]] == [-1_500, 10_000]
    assert page["items"][0]["balance_after_cents"] == 8_500


def test_reconciliation_after_many_operations(client, new_account):
    ana = new_account("Ana", 50_000)
    bia = new_account("Bia", 20_000)
    for amount in (1_000, 2_500, 333):
        transfer(client, ana, bia, amount)
        transfer(client, bia, ana, amount // 2)

    for account in (ana, bia):
        result = client.get(f"/accounts/{account}/reconciliation").json()
        assert result["consistent"] is True

    assert balance(client, ana) + balance(client, bia) == 70_000
