from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.db import SessionDep
from app.schemas import RefundCreate, to_response
from app.services import refunds

router = APIRouter(tags=["refunds"])


@router.post("/refund-requests")
def create_refund_request(
    body: RefundCreate,
    session: SessionDep,
    x_verification_token: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> JSONResponse:
    envelope = refunds.create_refund(
        session, token=x_verification_token, body=body, idempotency_key=idempotency_key
    )
    return to_response(envelope, 201 if envelope.code == "REFUND_CREATED" else 200)
