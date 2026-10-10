from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app import validation

Status = Literal["SUCCESS", "NEEDS_INFO", "REJECTED", "FAILED"]


class InvalidField(BaseModel):
    field: str
    reason: str


class Envelope(BaseModel):
    """The one response shape every endpoint returns."""

    status: Status
    code: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    invalid_fields: list[InvalidField] = Field(default_factory=list)


def to_response(envelope: Envelope, http_status: int = 200, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=http_status, content=jsonable_encoder(envelope), headers=headers)


# Real IDs are ~9 chars; the cap stops junk from being written to the operations log.
IdField = Annotated[str, Field(max_length=50)]


class VerificationRequest(BaseModel):
    customer_id: IdField
    policy_id: IdField
    date_of_birth: date
    session_id: str | None = Field(default=None, max_length=200)

    @field_validator("customer_id", "policy_id")
    @classmethod
    def _normalize_ids(cls, value: str) -> str:
        return validation.normalize_id(value)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def _parse_dob(cls, value: object) -> object:
        if isinstance(value, str) and value.strip():
            try:
                return date.fromisoformat(value.strip())
            except ValueError:
                raise ValueError("Date of birth must look like 1990-04-12") from None
        return value


class RefundCreate(BaseModel):
    policy_id: IdField
    amount: Decimal
    reason: str
    session_id: str | None = Field(default=None, max_length=200)

    @field_validator("policy_id")
    @classmethod
    def _normalize_policy_id(cls, value: str) -> str:
        return validation.normalize_id(value)

    @field_validator("amount")
    @classmethod
    def _check_amount(cls, value: Decimal) -> Decimal:
        return validation.validate_amount(value)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        return validation.normalize_reason(value)


class BankAccountUpdate(BaseModel):
    holder_name: str = Field(max_length=100)
    account_number: str
    ifsc: str
    session_id: str | None = Field(default=None, max_length=200)

    @field_validator("holder_name")
    @classmethod
    def _normalize_holder_name(cls, value: str) -> str:
        return validation.normalize_text(value)

    @field_validator("account_number")
    @classmethod
    def _normalize_account_number(cls, value: str) -> str:
        return validation.normalize_account_number(value)

    @field_validator("ifsc")
    @classmethod
    def _normalize_ifsc(cls, value: str) -> str:
        return validation.normalize_ifsc(value)
