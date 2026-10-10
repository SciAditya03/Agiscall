import secrets
from typing import Any, NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.models import RefundRequest
from app.schemas import Envelope, RefundCreate
from app.services.operations_log import CREATE_REFUND, record, reject
from app.services.policies import find_open_refund, get_policy
from app.services.verification import read_token
from app.validation import format_inr


def refund_view(refund: RefundRequest) -> dict[str, Any]:
    return {
        "id": refund.id,
        "policy_id": refund.policy_id,
        "customer_id": refund.customer_id,
        "amount": float(refund.amount),
        "reason": refund.reason,
        "status": refund.status,
        "session_id": refund.session_id,
        "created_at": refund.created_at.isoformat(),
    }


def _new_refund_id(session: Session) -> str:
    while True:
        candidate = f"RR-{secrets.randbelow(900_000) + 100_000}"
        if session.get(RefundRequest, candidate) is None:
            return candidate


def _find_by_key(session: Session, key: str) -> RefundRequest | None:
    return session.scalar(select(RefundRequest).where(RefundRequest.idempotency_key == key))


def _replay(existing: RefundRequest, body: RefundCreate) -> Envelope:
    if existing.policy_id != body.policy_id or existing.amount != body.amount:
        raise DomainError(
            ErrorCode.IDEMPOTENCY_KEY_CONFLICT,
            "That request ID was already used for a different refund.",
        )
    return Envelope(
        status="SUCCESS",
        code="REFUND_ALREADY_CREATED",
        message=f"Refund request {existing.id} was already submitted.",
        data={"refund": refund_view(existing)},
    )


def _open_refund_error(refund_id: str) -> DomainError:
    return DomainError(
        ErrorCode.REFUND_ALREADY_OPEN,
        f"There's already an open refund request, {refund_id}, on this policy.",
        data={"open_refund_id": refund_id},
    )


def create_refund(
    session: Session, *, token: str | None, body: RefundCreate, idempotency_key: str | None
) -> Envelope:
    customer_id = read_token(token)
    policy = get_policy(session, body.policy_id)
    if policy.customer_id != customer_id:
        raise DomainError(
            ErrorCode.TOKEN_SCOPE_MISMATCH,
            "You're verified for a different customer, so I can't act on this policy.",
        )

    key = (idempotency_key or "").strip() or None
    if key and (existing := _find_by_key(session, key)) is not None:
        return _replay(existing, body)

    def refuse(code: ErrorCode, message: str, data: dict[str, Any] | None = None) -> NoReturn:
        reject(
            session,
            operation_type=CREATE_REFUND,
            customer_id=customer_id,
            session_id=body.session_id,
            code=code,
            message=message,
            details={"policy_id": policy.id, "amount": str(body.amount)},
            data=data,
        )

    if policy.status != "ACTIVE":
        refuse(
            ErrorCode.POLICY_NOT_ACTIVE,
            f"Policy {policy.id} is {policy.status.lower()}, so a refund can't be raised on it.",
        )
    if body.amount > policy.premium_amount:
        refuse(
            ErrorCode.AMOUNT_EXCEEDS_PREMIUM,
            f"The refund amount {format_inr(body.amount)} is more than the premium of "
            f"{format_inr(policy.premium_amount)}.",
        )
    if (open_refund := find_open_refund(session, policy.id)) is not None:
        error = _open_refund_error(open_refund.id)
        refuse(error.code, error.message, error.data)

    refund = RefundRequest(
        id=_new_refund_id(session),
        policy_id=policy.id,
        customer_id=customer_id,
        amount=body.amount,
        reason=body.reason,
        status="SUBMITTED",
        session_id=body.session_id,
        idempotency_key=key,
    )
    session.add(refund)
    record(
        session,
        operation_type=CREATE_REFUND,
        customer_id=customer_id,
        session_id=body.session_id,
        status="SUCCESS",
        code="REFUND_CREATED",
        details={"refund_id": refund.id, "policy_id": policy.id, "amount": str(body.amount)},
    )
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request won the race on the idempotency key or the open-refund index.
        session.rollback()
        if key and (existing := _find_by_key(session, key)) is not None:
            return _replay(existing, body)
        if (open_refund := find_open_refund(session, policy.id)) is not None:
            error = _open_refund_error(open_refund.id)
            refuse(error.code, error.message, error.data)
        raise
    session.refresh(refund)

    return Envelope(
        status="SUCCESS",
        code="REFUND_CREATED",
        message=(
            f"Refund request {refund.id} for {format_inr(refund.amount)} "
            f"on policy {policy.id} has been submitted."
        ),
        data={"refund": refund_view(refund)},
    )
