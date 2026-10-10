from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.models import REFUND_OPEN_STATUSES, Policy, RefundRequest
from app.schemas import Envelope
from app.validation import clean_lookup_id


def get_policy(session: Session, policy_id: str) -> Policy:
    policy = session.get(Policy, clean_lookup_id(policy_id))
    if policy is None:
        raise DomainError(ErrorCode.POLICY_NOT_FOUND, "I couldn't find a policy with that number.")
    return policy


def find_open_refund(session: Session, policy_id: str) -> RefundRequest | None:
    stmt = (
        select(RefundRequest)
        .where(RefundRequest.policy_id == policy_id, RefundRequest.status.in_(REFUND_OPEN_STATUSES))
        .limit(1)
    )
    return session.scalar(stmt)


def lookup_policy(session: Session, policy_id: str) -> Envelope:
    policy = get_policy(session, policy_id)
    open_refund = find_open_refund(session, policy.id)
    return Envelope(
        status="SUCCESS",
        code="POLICY_FOUND",
        message=(
            f"Policy {policy.id} is a {policy.product_type.lower()} policy "
            f"and is currently {policy.status.lower()}."
        ),
        data={
            "policy": {
                "id": policy.id,
                "customer_id": policy.customer_id,
                "product_type": policy.product_type,
                "status": policy.status,
                "premium_amount": float(policy.premium_amount),
                "sum_insured": float(policy.sum_insured),
                "start_date": policy.start_date.isoformat(),
                "end_date": policy.end_date.isoformat(),
                "open_refund_id": open_refund.id if open_refund else None,
            }
        },
    )
