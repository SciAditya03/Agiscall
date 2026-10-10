"""Server-side caller verification.

The voice agent collects customer ID, policy number and date of birth; this service checks
them against the database and hands back a short-lived token scoped to that one customer.
Sensitive endpoints refuse to act without it, so the agent can't be talked past the check.
"""
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import DomainError, ErrorCode
from app.models import Customer, Policy
from app.schemas import Envelope, VerificationRequest
from app.services.operations_log import VERIFY, recent_failed_verifications, record, reject

SALT = "aegiscall-verification"
LOCKOUT_THRESHOLD = 3


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().token_secret, salt=SALT)


def issue_token(customer_id: str) -> str:
    return _serializer().dumps({"customer_id": customer_id})


def read_token(token: str | None) -> str:
    """Return the customer ID the token was issued for, or raise VERIFICATION_REQUIRED."""
    if not token:
        raise DomainError(ErrorCode.VERIFICATION_REQUIRED, "Please verify your identity first.")
    try:
        payload = _serializer().loads(token, max_age=get_settings().verification_ttl_seconds)
    except BadSignature:  # also covers SignatureExpired
        raise DomainError(
            ErrorCode.VERIFICATION_REQUIRED,
            "Your verification has expired or isn't valid. Please verify again.",
        ) from None
    customer_id = payload.get("customer_id") if isinstance(payload, dict) else None
    if not isinstance(customer_id, str):
        raise DomainError(ErrorCode.VERIFICATION_REQUIRED, "Please verify your identity first.")
    return customer_id


def verify_caller(session: Session, request: VerificationRequest) -> Envelope:
    customer = session.get(Customer, request.customer_id)
    customer_id = customer.id if customer else None

    if customer and recent_failed_verifications(session, customer.id) >= LOCKOUT_THRESHOLD:
        reject(
            session,
            operation_type=VERIFY,
            customer_id=customer_id,
            session_id=request.session_id,
            code=ErrorCode.VERIFICATION_LOCKED,
            message="Too many failed attempts. Please try again in 15 minutes.",
        )

    policy = session.get(Policy, request.policy_id)
    matches = (
        customer is not None
        and policy is not None
        and policy.customer_id == customer.id
        and customer.date_of_birth == request.date_of_birth
    )
    if not matches:
        reject(
            session,
            operation_type=VERIFY,
            customer_id=customer_id,
            session_id=request.session_id,
            code=ErrorCode.VERIFICATION_FAILED,
            message="Those details don't match our records.",
            details={"policy_id": request.policy_id},
        )

    record(
        session,
        operation_type=VERIFY,
        customer_id=customer.id,
        session_id=request.session_id,
        status="SUCCESS",
        code="VERIFIED",
        details={"policy_id": policy.id},
    )
    session.commit()
    ttl = get_settings().verification_ttl_seconds
    return Envelope(
        status="SUCCESS",
        code="VERIFIED",
        message=f"Thanks, {customer.full_name.split()[0]}. You're verified.",
        data={"token": issue_token(customer.id), "customer_id": customer.id, "expires_in_seconds": ttl},
    )
