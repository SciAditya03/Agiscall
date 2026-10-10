from app.models import RefundRequest

PUBLIC_PRIYA = {
    "id": "CUST-1001",
    "full_name": "Priya Sharma",
    "phone": "XXXXXX3210",
    "email": "p****@example.com",
}


def _auth(token):
    return {"X-Verification-Token": token}


def test_public_customer_view_hides_linking_details(client, seeded):
    response = client.get("/customers/CUST-1001")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "SUCCESS"
    assert body["code"] == "CUSTOMER_FOUND"
    # policy numbers and bank details would hand an unverified caller verification factors
    assert body["data"]["customer"] == PUBLIC_PRIYA
    assert "date_of_birth" not in response.text
    assert "1990-04-12" not in response.text


def test_verified_customer_view(client, seeded, verify):
    response = client.get("/customers/CUST-1001", headers=_auth(verify()))
    assert response.json()["data"]["customer"] == {
        **PUBLIC_PRIYA,
        "bank_account": {"holder_name": "Priya Sharma", "account_number": "XXXXXX7890", "ifsc": "HDFC0001234"},
        "policy_ids": ["POL-3001"],
    }
    assert "1990-04-12" not in response.text
    assert "50100234567890" not in response.text


def test_token_for_someone_else_gets_the_public_view(client, seeded, verify):
    meera_token = verify("CUST-1003", "POL-3003", "1978-01-25")
    response = client.get("/customers/CUST-1001", headers=_auth(meera_token))
    assert response.status_code == 200
    assert response.json()["data"]["customer"] == PUBLIC_PRIYA


def test_garbage_token_on_lookup_gets_the_public_view(client, seeded):
    response = client.get("/customers/CUST-1001", headers=_auth("garbage"))
    assert response.status_code == 200
    assert response.json()["data"]["customer"] == PUBLIC_PRIYA


def test_customer_without_bank_account(client, seeded, verify):
    token = verify("CUST-1004", "POL-3005", "1995-07-30")
    customer = client.get("/customers/CUST-1004", headers=_auth(token)).json()["data"]["customer"]
    assert customer["bank_account"] is None


def test_customer_with_two_policies(client, seeded, verify):
    token = verify("CUST-1003", "POL-3003", "1978-01-25")
    customer = client.get("/customers/CUST-1003", headers=_auth(token)).json()["data"]["customer"]
    assert customer["policy_ids"] == ["POL-3003", "POL-3004"]


def test_loosely_spoken_ids_resolve(client, seeded):
    assert client.get("/customers/cust1001").json()["data"]["customer"]["id"] == "CUST-1001"
    assert client.get("/policies/pol%203001").json()["data"]["policy"]["id"] == "POL-3001"


def test_unknown_customer(client, seeded):
    response = client.get("/customers/CUST-9999")
    assert response.status_code == 404
    assert response.json()["status"] == "REJECTED"
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"


def test_blank_customer_id_is_not_found(client, seeded):
    assert client.get("/customers/%20").json()["code"] == "CUSTOMER_NOT_FOUND"


def test_public_policy_view_hides_customer_id(client, seeded):
    response = client.get("/policies/POL-3001")
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == "POLICY_FOUND"
    assert body["message"] == "Policy POL-3001 is a health policy and is currently active."
    assert body["data"]["policy"] == {
        "id": "POL-3001",
        "product_type": "HEALTH",
        "status": "ACTIVE",
        "premium_amount": 18000.0,
        "sum_insured": 500000.0,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "open_refund_id": None,
    }


def test_verified_policy_view_includes_customer_id(client, seeded, verify):
    policy = client.get("/policies/POL-3001", headers=_auth(verify())).json()["data"]["policy"]
    assert policy["customer_id"] == "CUST-1001"


def test_policy_shows_open_refund(client, seeded):
    seeded.add(RefundRequest(id="RR-123456", policy_id="POL-3001", customer_id="CUST-1001",
                             amount=500, reason="test", status="SUBMITTED"))
    seeded.commit()
    assert client.get("/policies/POL-3001").json()["data"]["policy"]["open_refund_id"] == "RR-123456"


def test_unknown_policy(client, seeded):
    response = client.get("/policies/POL-9999")
    assert response.status_code == 404
    assert response.json()["code"] == "POLICY_NOT_FOUND"
