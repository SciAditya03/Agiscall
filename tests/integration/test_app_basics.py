from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.errors import DomainError, ErrorCode
from app.main import create_app
from app.schemas import BankAccountUpdate, RefundCreate, VerificationRequest
from app.workflows import WORKFLOWS

ENVELOPE_KEYS = {"status", "code", "message", "data", "missing_fields", "invalid_fields"}


@pytest.fixture
def probe_client():
    """An app with a few throwaway routes to exercise the exception handlers (no DB)."""
    app = create_app()

    @app.post("/_probe/refund")
    def probe_refund(body: RefundCreate):
        return {"ok": True}

    @app.get("/_probe/domain-error")
    def probe_domain_error():
        raise DomainError(ErrorCode.POLICY_NOT_ACTIVE, "Policy POL-3002 is lapsed.", data={"policy_id": "POL-3002"})

    @app.get("/_probe/crash")
    def probe_crash():
        raise RuntimeError("boom: secret internals")

    return TestClient(app, raise_server_exceptions=False)


def test_health(probe_client):
    response = probe_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "SUCCESS", "code": "OK", "message": "Service is healthy.",
        "data": {}, "missing_fields": [], "invalid_fields": [],
    }


def test_missing_fields_are_all_listed(probe_client):
    response = probe_client.post("/_probe/refund", json={})
    body = response.json()
    assert response.status_code == 422
    assert body["status"] == "NEEDS_INFO"
    assert body["code"] == "MISSING_FIELDS"
    assert body["missing_fields"] == ["policy_id", "amount", "reason"]
    assert "policy_id, amount, reason" in body["message"]


def test_invalid_fields_carry_readable_reasons(probe_client):
    response = probe_client.post("/_probe/refund", json={"policy_id": "POL-3001", "amount": "-5", "reason": "no"})
    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "INVALID_FIELDS"
    assert body["missing_fields"] == []
    assert body["invalid_fields"] == [
        {"field": "amount", "reason": "Amount must be greater than zero"},
        {"field": "reason", "reason": "Reason must be between 3 and 500 characters"},
    ]


def test_missing_wins_over_invalid_in_code(probe_client):
    body = probe_client.post("/_probe/refund", json={"policy_id": "POL-3001", "amount": "-5"}).json()
    assert body["code"] == "MISSING_FIELDS"
    assert body["missing_fields"] == ["reason"]
    assert [f["field"] for f in body["invalid_fields"]] == ["amount"]


@pytest.mark.parametrize("raw_body", ['{"policy_id": ', "[]", '"just a string"'])
def test_malformed_or_non_object_json_is_needs_info(probe_client, raw_body):
    response = probe_client.post(
        "/_probe/refund", content=raw_body, headers={"content-type": "application/json"}
    )
    body = response.json()
    assert response.status_code == 422
    assert set(body) == ENVELOPE_KEYS
    assert body["status"] == "NEEDS_INFO"


def test_domain_error_becomes_rejected_envelope(probe_client):
    response = probe_client.get("/_probe/domain-error")
    assert response.status_code == 409
    assert response.json() == {
        "status": "REJECTED", "code": "POLICY_NOT_ACTIVE", "message": "Policy POL-3002 is lapsed.",
        "data": {"policy_id": "POL-3002"}, "missing_fields": [], "invalid_fields": [],
    }


def test_unexpected_error_is_failed_without_internals(probe_client):
    response = probe_client.get("/_probe/crash")
    body = response.json()
    assert response.status_code == 500
    assert body["status"] == "FAILED"
    assert body["code"] == "INTERNAL_ERROR"
    assert "boom" not in response.text


def test_unknown_route_uses_envelope(probe_client):
    response = probe_client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "ROUTE_NOT_FOUND"
    assert set(response.json()) == ENVELOPE_KEYS


def test_wrong_method_uses_envelope(probe_client):
    response = probe_client.delete("/health")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_request_models_normalize_values():
    refund = RefundCreate(policy_id="pol 3001", amount="1200.50", reason="  double   charged ")
    assert (refund.policy_id, refund.amount, refund.reason) == ("POL-3001", Decimal("1200.50"), "double charged")

    bank = BankAccountUpdate(holder_name=" priya  sharma ", account_number="5010 0234 5678 90", ifsc="hdfc0001234")
    assert (bank.holder_name, bank.account_number, bank.ifsc) == ("priya sharma", "50100234567890", "HDFC0001234")

    verification = VerificationRequest(customer_id="cust1001", policy_id="pol-3001", date_of_birth="1990-04-12")
    assert (verification.customer_id, verification.policy_id) == ("CUST-1001", "POL-3001")


@pytest.mark.parametrize(
    ("workflow_key", "model"),
    [("REQUEST_REFUND", RefundCreate), ("UPDATE_BANK_ACCOUNT", BankAccountUpdate)],
)
def test_workflow_required_fields_match_request_models(workflow_key, model):
    required = [name for name, field in model.model_fields.items() if field.is_required()]
    assert tuple(required) == WORKFLOWS[workflow_key].required_fields
