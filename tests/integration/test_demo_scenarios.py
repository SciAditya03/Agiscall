"""The seven demo scenarios from the design spec (§9), end to end through the API."""
from sqlalchemy import func, select

from app.models import RefundRequest

PRIYA = {"customer_id": "CUST-1001", "policy_id": "POL-3001", "date_of_birth": "1990-04-12"}


def test_1_policy_status_lookup(client, seeded):
    body = client.get("/policies/POL-3001").json()
    assert (body["status"], body["code"]) == ("SUCCESS", "POLICY_FOUND")
    assert body["data"]["policy"]["status"] == "ACTIVE"


def test_2_verify_then_refund(client, seeded, verify):
    response = client.post(
        "/refund-requests",
        json={"policy_id": "POL-3001", "amount": 1200, "reason": "Charged twice for March premium"},
        headers={"X-Verification-Token": verify()},
    )
    assert (response.json()["status"], response.json()["code"]) == ("SUCCESS", "REFUND_CREATED")


def test_3_refund_without_amount_needs_info(client, seeded, verify):
    response = client.post(
        "/refund-requests",
        json={"policy_id": "POL-3001", "reason": "Charged twice"},
        headers={"X-Verification-Token": verify()},
    )
    body = response.json()
    assert (body["status"], body["code"], body["missing_fields"]) == ("NEEDS_INFO", "MISSING_FIELDS", ["amount"])


def test_4_bank_update_without_token(client, seeded):
    response = client.patch(
        "/customers/CUST-1001/bank-account",
        json={"holder_name": "Priya Sharma", "account_number": "123456789012", "ifsc": "ICIC0000789"},
    )
    assert (response.json()["status"], response.json()["code"]) == ("REJECTED", "VERIFICATION_REQUIRED")


def test_5_three_wrong_dobs_lock_verification(client, seeded):
    for _ in range(3):
        client.post("/verifications", json={**PRIYA, "date_of_birth": "1991-01-01"})
    response = client.post("/verifications", json=PRIYA)
    assert (response.json()["status"], response.json()["code"]) == ("REJECTED", "VERIFICATION_LOCKED")


def test_6_bank_update_to_someone_elses_name(client, seeded, verify):
    response = client.patch(
        "/customers/CUST-1001/bank-account",
        json={"holder_name": "Rahul Mehta", "account_number": "123456789012", "ifsc": "ICIC0000789"},
        headers={"X-Verification-Token": verify()},
    )
    assert (response.json()["status"], response.json()["code"]) == ("REJECTED", "HOLDER_NAME_MISMATCH")


def test_7_retry_with_same_idempotency_key(client, seeded, verify):
    headers = {"X-Verification-Token": verify(), "Idempotency-Key": "demo-call-1"}
    body = {"policy_id": "POL-3001", "amount": 1200, "reason": "Charged twice for March premium"}
    first = client.post("/refund-requests", json=body, headers=headers)
    second = client.post("/refund-requests", json=body, headers=headers)
    assert (first.status_code, second.status_code) == (201, 200)
    seeded.expire_all()
    assert seeded.scalar(select(func.count()).select_from(RefundRequest)) == 1
