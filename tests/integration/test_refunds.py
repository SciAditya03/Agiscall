from sqlalchemy import func, select

from app.models import Operation, RefundRequest

REFUND = {"policy_id": "POL-3001", "amount": 1200, "reason": "Charged twice for March premium"}


def _post(client, token=None, body=REFUND, key=None):
    headers = {}
    if token:
        headers["X-Verification-Token"] = token
    if key:
        headers["Idempotency-Key"] = key
    return client.post("/refund-requests", json=body, headers=headers)


def _refund_count(db):
    return db.scalar(select(func.count()).select_from(RefundRequest))


def test_create_refund(client, seeded, verify):
    response = _post(client, verify(), {**REFUND, "session_id": "sess-42"})
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "SUCCESS"
    assert body["code"] == "REFUND_CREATED"
    refund = body["data"]["refund"]
    assert refund["id"].startswith("RR-") and len(refund["id"]) == 9
    assert refund["policy_id"] == "POL-3001"
    assert refund["customer_id"] == "CUST-1001"
    assert refund["amount"] == 1200.0
    assert refund["status"] == "SUBMITTED"
    assert refund["session_id"] == "sess-42"
    assert refund["created_at"]
    assert body["message"] == f"Refund request {refund['id']} for ₹1,200.00 on policy POL-3001 has been submitted."

    seeded.expire_all()
    operation = seeded.scalars(select(Operation).where(Operation.operation_type == "CREATE_REFUND")).one()
    assert (operation.status, operation.code, operation.session_id) == ("SUCCESS", "REFUND_CREATED", "sess-42")


def test_requires_token(client, seeded):
    response = _post(client)
    assert response.status_code == 401
    assert response.json()["code"] == "VERIFICATION_REQUIRED"
    assert _refund_count(seeded) == 0


def test_rejects_garbage_token(client, seeded):
    assert _post(client, "not-a-token").json()["code"] == "VERIFICATION_REQUIRED"


def test_token_check_comes_before_existence_check(client, seeded):
    response = _post(client, body={**REFUND, "policy_id": "POL-9999"})
    assert response.json()["code"] == "VERIFICATION_REQUIRED"


def test_unknown_policy_with_token(client, seeded, verify):
    response = _post(client, verify(), {**REFUND, "policy_id": "POL-9999"})
    assert response.status_code == 404
    assert response.json()["code"] == "POLICY_NOT_FOUND"


def test_token_for_another_customer(client, seeded, verify):
    meera_token = verify("CUST-1003", "POL-3003", "1978-01-25")
    response = _post(client, meera_token)
    assert response.status_code == 403
    assert response.json()["code"] == "TOKEN_SCOPE_MISMATCH"
    assert _refund_count(seeded) == 0


def test_lapsed_policy_is_rejected_and_logged(client, seeded, verify):
    token = verify("CUST-1002", "POL-3002", "1985-11-02")
    response = _post(client, token, {**REFUND, "policy_id": "POL-3002"})
    assert response.status_code == 409
    assert response.json()["code"] == "POLICY_NOT_ACTIVE"
    seeded.expire_all()
    operation = seeded.scalars(select(Operation).where(Operation.operation_type == "CREATE_REFUND")).one()
    assert (operation.status, operation.code) == ("REJECTED", "POLICY_NOT_ACTIVE")


def test_amount_above_premium_is_rejected(client, seeded, verify):
    response = _post(client, verify(), {**REFUND, "amount": "18000.01"})
    assert response.status_code == 409
    assert response.json()["code"] == "AMOUNT_EXCEEDS_PREMIUM"


def test_amount_equal_to_premium_is_fine(client, seeded, verify):
    assert _post(client, verify(), {**REFUND, "amount": "18000.00"}).status_code == 201


def test_only_one_open_refund_per_policy(client, seeded, verify):
    token = verify()
    first = _post(client, token).json()["data"]["refund"]["id"]
    response = _post(client, token, {**REFUND, "amount": 300})
    assert response.status_code == 409
    assert response.json()["code"] == "REFUND_ALREADY_OPEN"
    assert response.json()["data"] == {"open_refund_id": first}


def test_customer_with_two_policies_can_refund_each(client, seeded, verify):
    token = verify("CUST-1003", "POL-3003", "1978-01-25")
    assert _post(client, token, {**REFUND, "policy_id": "POL-3003"}).status_code == 201
    assert _post(client, token, {**REFUND, "policy_id": "POL-3004"}).status_code == 201


def test_idempotent_retry_returns_the_same_refund(client, seeded, verify):
    token = verify()
    first = _post(client, token, key="call-7-refund")
    second = _post(client, token, key="call-7-refund")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["code"] == "REFUND_ALREADY_CREATED"
    assert second.json()["data"]["refund"]["id"] == first.json()["data"]["refund"]["id"]
    assert _refund_count(seeded) == 1


def test_idempotency_key_reused_for_a_different_refund(client, seeded, verify):
    token = verify()
    _post(client, token, key="call-7-refund")
    response = _post(client, token, {**REFUND, "amount": 999}, key="call-7-refund")
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    assert "refund" not in response.json()["data"]


def test_other_customers_key_never_returns_their_refund(client, seeded, verify):
    _post(client, verify(), key="shared-key")
    meera_token = verify("CUST-1003", "POL-3003", "1978-01-25")
    response = _post(client, meera_token, {**REFUND, "policy_id": "POL-3003"}, key="shared-key")
    assert response.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_missing_amount_needs_info(client, seeded, verify):
    response = _post(client, verify(), {"policy_id": "POL-3001", "reason": "Charged twice"})
    assert response.status_code == 422
    assert response.json()["missing_fields"] == ["amount"]
