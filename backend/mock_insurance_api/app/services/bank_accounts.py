from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.schemas import BankAccountUpdate, Envelope
from app.services.customers import bank_view, get_customer
from app.services.operations_log import UPDATE_BANK_ACCOUNT, record, reject
from app.services.verification import read_token
from app.validation import mask_account, names_match


def update_bank_account(
    session: Session, *, token: str | None, customer_id: str, body: BankAccountUpdate
) -> Envelope:
    token_customer_id = read_token(token)
    customer = get_customer(session, customer_id)
    if token_customer_id != customer.id:
        raise DomainError(
            ErrorCode.TOKEN_SCOPE_MISMATCH,
            "You're verified for a different customer, so I can't change this account.",
        )

    if not names_match(body.holder_name, customer.full_name):
        reject(
            session,
            operation_type=UPDATE_BANK_ACCOUNT,
            customer_id=customer.id,
            session_id=body.session_id,
            code=ErrorCode.HOLDER_NAME_MISMATCH,
            message="The account holder name has to match the name on the policy, so I can't make this change.",
        )
    if customer.bank_account_number == body.account_number and customer.bank_ifsc == body.ifsc:
        reject(
            session,
            operation_type=UPDATE_BANK_ACCOUNT,
            customer_id=customer.id,
            session_id=body.session_id,
            code=ErrorCode.SAME_ACCOUNT,
            message="That's the same bank account we already have on file.",
        )

    old_account = mask_account(customer.bank_account_number) if customer.bank_account_number else None
    customer.bank_holder_name = customer.full_name
    customer.bank_account_number = body.account_number
    customer.bank_ifsc = body.ifsc
    customer.updated_at = datetime.now(UTC)
    record(
        session,
        operation_type=UPDATE_BANK_ACCOUNT,
        customer_id=customer.id,
        session_id=body.session_id,
        status="SUCCESS",
        code="BANK_ACCOUNT_UPDATED",
        details={"old_account": old_account, "new_account": mask_account(body.account_number), "ifsc": body.ifsc},
    )
    session.commit()

    return Envelope(
        status="SUCCESS",
        code="BANK_ACCOUNT_UPDATED",
        message=f"Your refund account has been updated to the account ending {body.account_number[-4:]}.",
        data={"bank_account": bank_view(customer)},
    )
