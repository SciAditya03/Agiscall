import json

from sqlalchemy import select

from app.models import Customer, Operation

NEW_ACCOUNT = {"holder_name": "Priya Sharma", "account_number": "123456789012345", "ifsc": "ICIC0000789"}


def _patch(client, customer_id="CUST-1001", token=None, body=NEW_ACCOUNT):
    headers = {"X-Verification-Token": token} if token else {}
    return client.patch(f"/customers/{customer_id}/bank-account", json=body, headers=headers)


def test_update_bank_account(client, seeded, verify):
    response = _patch(client, token=verify(), body={**NEW_ACCOUNT, "session_id": "sess-9"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "SUCCESS"
    assert body["code"] == "BANK_ACCOUNT_UPDATED"
    assert body["data"]["bank_account"] == {
        "holder_name": "Priya Sharma", "account_number": "XXXXXX2345", "ifsc": "ICIC0000789",
    }
    assert "123456789012345" not in response.text
    assert body["message"] == "Your refund account has been updated to the account ending 2345."

    seeded.expire_all()
    customer = seeded.get(Customer, "CUST-1001")
    assert (customer.bank_account_number, customer.bank_ifsc) == ("123456789012345", "ICIC0000789")

    operation = seeded.scalars(select(Operation).where(Operation.operation_type == "UPDATE_BANK_ACCOUNT")).one()
    assert (operation.status, operation.code, operation.session_id) == ("SUCCESS", "BANK_ACCOUNT_UPDATED", "sess-9")
    assert operation.details == {"old_account": "XXXXXX7890", "new_account": "XXXXXX2345", "ifsc": "ICIC0000789"}
    raw_details = json.dumps(operation.details)
    assert "50100234567890" not in raw_details and "123456789012345" not in raw_details


def test_holder_name_ignores_case_and_spacing(client, seeded, verify):
    assert _patch(client, token=verify(), body={**NEW_ACCOUNT, "holder_name": "  priya   SHARMA "}).status_code == 200


def test_customer_without_previous_account(client, seeded, verify):
    token = verify("CUST-1004", "POL-3005", "1995-07-30")
    response = _patch(client, "CUST-1004", token, {**NEW_ACCOUNT, "holder_name": "Rohan Gupta"})
    assert response.status_code == 200
    seeded.expire_all()
    operation = seeded.scalars(select(Operation).where(Operation.operation_type == "UPDATE_BANK_ACCOUNT")).one()
    assert operation.details["old_account"] is None


def test_requires_token(client, seeded):
    response = _patch(client)
    assert response.status_code == 401
    assert response.json()["code"] == "VERIFICATION_REQUIRED"


def test_token_check_comes_before_existence_check(client, seeded):
    assert _patch(client, "CUST-9999").json()["code"] == "VERIFICATION_REQUIRED"


def test_unknown_customer_with_token(client, seeded, verify):
    response = _patch(client, "CUST-9999", verify())
    assert response.status_code == 404
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"


def test_token_for_another_customer(client, seeded, verify):
    meera_token = verify("CUST-1003", "POL-3003", "1978-01-25")
    response = _patch(client, "CUST-1001", meera_token)
    assert response.status_code == 403
    assert response.json()["code"] == "TOKEN_SCOPE_MISMATCH"
    seeded.expire_all()
    assert seeded.get(Customer, "CUST-1001").bank_account_number == "50100234567890"


def test_holder_name_mismatch_is_rejected_and_logged(client, seeded, verify):
    response = _patch(client, token=verify(), body={**NEW_ACCOUNT, "holder_name": "Rahul Mehta"})
    assert response.status_code == 403
    assert response.json()["code"] == "HOLDER_NAME_MISMATCH"
    seeded.expire_all()
    assert seeded.get(Customer, "CUST-1001").bank_account_number == "50100234567890"
    operation = seeded.scalars(select(Operation).where(Operation.operation_type == "UPDATE_BANK_ACCOUNT")).one()
    assert (operation.status, operation.code) == ("REJECTED", "HOLDER_NAME_MISMATCH")


def test_same_account_is_rejected(client, seeded, verify):
    same = {"holder_name": "Priya Sharma", "account_number": "5010 0234 5678 90", "ifsc": "hdfc0001234"}
    response = _patch(client, token=verify(), body=same)
    assert response.status_code == 409
    assert response.json()["code"] == "SAME_ACCOUNT"


def test_invalid_account_and_ifsc_listed_together(client, seeded, verify):
    response = _patch(client, token=verify(), body={**NEW_ACCOUNT, "account_number": "123", "ifsc": "BAD"})
    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "INVALID_FIELDS"
    assert [item["field"] for item in body["invalid_fields"]] == ["account_number", "ifsc"]


def test_loose_customer_id_in_path(client, seeded, verify):
    assert _patch(client, "cust1001", verify()).status_code == 200
