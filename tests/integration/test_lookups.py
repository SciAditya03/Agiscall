from app.models import RefundRequest


def test_get_customer_masks_contact_details_and_hides_dob(client, seeded):
    response = client.get("/customers/CUST-1001")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "SUCCESS"
    assert body["code"] == "CUSTOMER_FOUND"
    customer = body["data"]["customer"]
    assert customer == {
        "id": "CUST-1001",
        "full_name": "Priya Sharma",
        "phone": "XXXXXX3210",
        "email": "p****@example.com",
        "bank_account": {"holder_name": "Priya Sharma", "account_number": "XXXXXX7890", "ifsc": "HDFC0001234"},
        "policy_ids": ["POL-3001"],
    }
    assert "date_of_birth" not in response.text
    assert "1990-04-12" not in response.text
    assert "50100234567890" not in response.text


def test_customer_without_bank_account(client, seeded):
    customer = client.get("/customers/CUST-1004").json()["data"]["customer"]
    assert customer["bank_account"] is None


def test_customer_with_two_policies(client, seeded):
    assert client.get("/customers/CUST-1003").json()["data"]["customer"]["policy_ids"] == ["POL-3003", "POL-3004"]


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


def test_get_policy(client, seeded):
    response = client.get("/policies/POL-3001")
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == "POLICY_FOUND"
    assert body["message"] == "Policy POL-3001 is a health policy and is currently active."
    assert body["data"]["policy"] == {
        "id": "POL-3001",
        "customer_id": "CUST-1001",
        "product_type": "HEALTH",
        "status": "ACTIVE",
        "premium_amount": 18000.0,
        "sum_insured": 500000.0,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "open_refund_id": None,
    }


def test_policy_shows_open_refund(client, seeded):
    seeded.add(RefundRequest(id="RR-123456", policy_id="POL-3001", customer_id="CUST-1001",
                             amount=500, reason="test", status="SUBMITTED"))
    seeded.commit()
    assert client.get("/policies/POL-3001").json()["data"]["policy"]["open_refund_id"] == "RR-123456"


def test_unknown_policy(client, seeded):
    response = client.get("/policies/POL-9999")
    assert response.status_code == 404
    assert response.json()["code"] == "POLICY_NOT_FOUND"
