"""Writes to the operations table (audit log) and the lockout query."""
from datetime import timedelta
from typing import Any, NoReturn

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.models import Operation

VERIFY = "VERIFY"
CREATE_REFUND = "CREATE_REFUND"
UPDATE_BANK_ACCOUNT = "UPDATE_BANK_ACCOUNT"

LOCKOUT_WINDOW = timedelta(minutes=15)


def record(
    session: Session,
    *,
    operation_type: str,
    customer_id: str | None,
    session_id: str | None,
    status: str,
    code: str,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        Operation(
            operation_type=operation_type,
            customer_id=customer_id,
            session_id=session_id,
            status=status,
            code=str(code),
            details=details or {},
        )
    )


def reject(
    session: Session,
    *,
    operation_type: str,
    customer_id: str | None,
    session_id: str | None,
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> NoReturn:
    """Log a refused operation, commit the log row, then raise."""
    record(
        session,
        operation_type=operation_type,
        customer_id=customer_id,
        session_id=session_id,
        status="REJECTED",
        code=code,
        details=details,
    )
    session.commit()
    raise DomainError(code, message, data=data)


def recent_failed_verifications(session: Session, customer_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(Operation)
        .where(
            Operation.customer_id == customer_id,
            Operation.operation_type == VERIFY,
            Operation.code == ErrorCode.VERIFICATION_FAILED.value,
            Operation.created_at >= func.now() - LOCKOUT_WINDOW,
        )
    )
    return session.scalar(stmt) or 0
