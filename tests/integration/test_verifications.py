from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.errors import DomainError
from app.models import Operation
from app.schemas import VerificationRequest
from app.services.verification import SALT, issue_token, read_token, verify_caller

PRIYA = {"customer_id": "CUST-1001", "policy_id": "POL-3001", "date_of_birth": "1990-04-12"}
WRONG_DOB = {**PRIYA, "date_of_birth": "1990-04-13"}


def _operations(db):
    db.expire_all()
    return list(db.scalars(select(Operation).order_by(Operation.id)))


# --- tokens (no DB) -------------------------------------------------------

def test_token_round_trip():
    assert read_token(issue_token("CUST-1001")) == "CUST-1001"


@pytest.mark.parametrize("token", [None, "", "garbage"])
def test_missing_or_garbage_token_requires_verification(token):
    with pytest.raises(DomainError) as excinfo:
        read_token(token)
    assert excinfo.value.code == "VERIFICATION_REQUIRED"


def test_token_signed_with_another_secret_is_rejected():
    forged = URLSafeTimedSerializer("not-our-secret", salt=SALT).dumps({"customer_id": "CUST-1001"})
    with pytest.raises(DomainError) as excinfo:
        read_token(forged)
    assert excinfo.value.code == "VERIFICATION_REQUIRED"


def test_expired_token_is_rejected(monkeypatch):
    token = issue_token("CUST-1001")
    monkeypatch.setattr(get_settings(), "verification_ttl_seconds", -1)
    with pytest.raises(DomainError) as excinfo:
        read_token(token)
    assert excinfo.value.code == "VERIFICATION_REQUIRED"


# --- POST /verifications --------------------------------------------------

def test_successful_verification(client, seeded):
    response = client.post("/verifications", json={**PRIYA, "session_id": "sess-1"})
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "SUCCESS"
    assert body["code"] == "VERIFIED"
    assert body["data"]["customer_id"] == "CUST-1001"
    assert body["data"]["expires_in_seconds"] == 600
    assert read_token(body["data"]["token"]) == "CUST-1001"

    [operation] = _operations(seeded)
    assert (operation.operation_type, operation.status, operation.code) == ("VERIFY", "SUCCESS", "VERIFIED")
    assert operation.session_id == "sess-1"
    assert "1990-04-12" not in str(operation.details)


def test_loose_ids_verify(client, seeded):
    response = client.post("/verifications", json={**PRIYA, "customer_id": "cust1001", "policy_id": "pol 3001"})
    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        WRONG_DOB,
        {**PRIYA, "policy_id": "POL-3003"},      # someone else's policy
        {**PRIYA, "policy_id": "POL-9999"},      # unknown policy
        {**PRIYA, "customer_id": "CUST-9999"},   # unknown customer
    ],
)
def test_failed_verification_does_not_say_which_detail_was_wrong(client, seeded, payload):
    response = client.post("/verifications", json=payload)
    body = response.json()
    assert response.status_code == 401
    assert body["code"] == "VERIFICATION_FAILED"
    assert body["message"] == "Those details don't match our records."


def test_failure_is_logged_without_dob(client, seeded):
    client.post("/verifications", json=WRONG_DOB)
    [operation] = _operations(seeded)
    assert (operation.customer_id, operation.status, operation.code) == ("CUST-1001", "REJECTED", "VERIFICATION_FAILED")
    assert "1990-04-13" not in str(operation.details)


def test_three_failures_lock_the_customer(client, seeded):
    for _ in range(3):
        assert client.post("/verifications", json=WRONG_DOB).json()["code"] == "VERIFICATION_FAILED"

    response = client.post("/verifications", json=PRIYA)
    assert response.status_code == 423
    assert response.json()["code"] == "VERIFICATION_LOCKED"


def test_lockout_is_per_customer(client, seeded):
    for _ in range(3):
        client.post("/verifications", json=WRONG_DOB)
    meera = {"customer_id": "CUST-1003", "policy_id": "POL-3003", "date_of_birth": "1978-01-25"}
    assert client.post("/verifications", json=meera).status_code == 201


def test_old_failures_do_not_lock(client, seeded):
    old = datetime.now(UTC) - timedelta(minutes=16)
    for _ in range(3):
        seeded.add(Operation(operation_type="VERIFY", customer_id="CUST-1001", status="REJECTED",
                             code="VERIFICATION_FAILED", details={}, created_at=old))
    seeded.commit()
    assert client.post("/verifications", json=PRIYA).status_code == 201


def test_unknown_customer_failures_are_logged_without_customer(client, seeded):
    client.post("/verifications", json={**PRIYA, "customer_id": "CUST-9999"})
    [operation] = _operations(seeded)
    assert operation.customer_id is None


def test_missing_dob_needs_info(client, seeded):
    response = client.post("/verifications", json={"customer_id": "CUST-1001", "policy_id": "POL-3001"})
    assert response.status_code == 422
    assert response.json()["missing_fields"] == ["date_of_birth"]


def test_parallel_wrong_guesses_cannot_beat_the_lockout(clean_engine, seeded):
    factory = sessionmaker(bind=clean_engine, expire_on_commit=False)
    request = VerificationRequest(**WRONG_DOB)

    def attempt(_):
        with factory() as session:
            try:
                verify_caller(session, request)
            except DomainError as error:
                return error.code.value

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(attempt, range(10)))

    assert codes.count("VERIFICATION_FAILED") == 3
    assert codes.count("VERIFICATION_LOCKED") == 7


def test_successful_verification_resets_the_failure_count(client, seeded):
    for _ in range(2):
        client.post("/verifications", json=WRONG_DOB)
    assert client.post("/verifications", json=PRIYA).status_code == 201
    client.post("/verifications", json=WRONG_DOB)  # a typo when re-verifying later
    assert client.post("/verifications", json=PRIYA).status_code == 201
