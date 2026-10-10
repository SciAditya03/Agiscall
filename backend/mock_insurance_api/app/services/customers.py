from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.models import Customer, Policy
from app.schemas import Envelope
from app.validation import clean_lookup_id, mask_account, mask_email, mask_phone


def get_customer(session: Session, customer_id: str) -> Customer:
    customer = session.get(Customer, clean_lookup_id(customer_id))
    if customer is None:
        raise DomainError(ErrorCode.CUSTOMER_NOT_FOUND, "I couldn't find a customer with that ID.")
    return customer


def bank_view(customer: Customer) -> dict[str, str] | None:
    if not customer.bank_account_number:
        return None
    return {
        "holder_name": customer.bank_holder_name,
        "account_number": mask_account(customer.bank_account_number),
        "ifsc": customer.bank_ifsc,
    }


def lookup_customer(session: Session, customer_id: str) -> Envelope:
    customer = get_customer(session, customer_id)
    policy_ids = list(
        session.scalars(select(Policy.id).where(Policy.customer_id == customer.id).order_by(Policy.id))
    )
    return Envelope(
        status="SUCCESS",
        code="CUSTOMER_FOUND",
        message=f"Found customer {customer.full_name}.",
        data={
            "customer": {
                "id": customer.id,
                "full_name": customer.full_name,
                "phone": mask_phone(customer.phone),
                "email": mask_email(customer.email),
                "bank_account": bank_view(customer),
                "policy_ids": policy_ids,
            }
        },
    )
