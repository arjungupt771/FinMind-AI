def _sample_transaction(amount=500.0, tx_type="expense", category="Food"):
    return {
        "date": "2026-09-01T00:00:00",
        "merchant": "Test Merchant",
        "amount": amount,
        "type": tx_type,
        "category": category,
        "source": "test",
        "description": "unit test transaction",
    }


def test_add_and_list_transaction(client):
    create_resp = client.post("/transactions/", json=_sample_transaction())
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["merchant"] == "Test Merchant"
    assert created["amount"] == 500.0

    list_resp = client.get("/transactions/")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]


def test_get_transaction_not_found(client):
    resp = client.get("/transactions/does-not-exist")
    assert resp.status_code == 404


def test_update_transaction(client):
    created = client.post("/transactions/", json=_sample_transaction()).json()

    updated_payload = _sample_transaction(amount=750.0, category="Travel")
    update_resp = client.put(f"/transactions/{created['id']}", json=updated_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["amount"] == 750.0
    assert update_resp.json()["category"] == "Travel"


def test_delete_transaction(client):
    created = client.post("/transactions/", json=_sample_transaction()).json()

    delete_resp = client.delete(f"/transactions/{created['id']}")
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/transactions/{created['id']}")
    assert get_resp.status_code == 404


def test_bulk_upload(client):
    payload = [_sample_transaction(amount=100.0), _sample_transaction(amount=200.0, category="Bills")]
    resp = client.post("/transactions/bulk-upload", json=payload)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_category_filter(client):
    client.post("/transactions/", json=_sample_transaction(category="Food"))
    client.post("/transactions/", json=_sample_transaction(category="Travel"))

    resp = client.get("/transactions/", params={"category": "Travel"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["category"] == "Travel"


def test_user_isolation(client):
    """A transaction created for one user should not be visible to another."""
    client.post(
        "/transactions/",
        json=_sample_transaction(),
        headers={"X-User-Id": "user-a"},
    )
    resp = client.get("/transactions/", headers={"X-User-Id": "user-b"})
    assert resp.status_code == 200
    assert resp.json() == []