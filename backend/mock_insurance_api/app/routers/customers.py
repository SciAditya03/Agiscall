from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.db import SessionDep
from app.schemas import BankAccountUpdate, to_response
from app.services import bank_accounts, customers

router = APIRouter(tags=["customers"])


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    session: SessionDep,
    x_verification_token: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    return to_response(customers.lookup_customer(session, customer_id, x_verification_token))


@router.patch("/customers/{customer_id}/bank-account")
def update_bank_account(
    customer_id: str,
    body: BankAccountUpdate,
    session: SessionDep,
    x_verification_token: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    envelope = bank_accounts.update_bank_account(
        session, token=x_verification_token, customer_id=customer_id, body=body
    )
    return to_response(envelope)
