from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    MISSING_FIELDS = "MISSING_FIELDS"
    INVALID_FIELDS = "INVALID_FIELDS"
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFICATION_LOCKED = "VERIFICATION_LOCKED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    TOKEN_SCOPE_MISMATCH = "TOKEN_SCOPE_MISMATCH"
    POLICY_NOT_ACTIVE = "POLICY_NOT_ACTIVE"
    AMOUNT_EXCEEDS_PREMIUM = "AMOUNT_EXCEEDS_PREMIUM"
    REFUND_ALREADY_OPEN = "REFUND_ALREADY_OPEN"
    IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"
    HOLDER_NAME_MISMATCH = "HOLDER_NAME_MISMATCH"
    SAME_ACCOUNT = "SAME_ACCOUNT"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.MISSING_FIELDS: 422,
    ErrorCode.INVALID_FIELDS: 422,
    ErrorCode.CUSTOMER_NOT_FOUND: 404,
    ErrorCode.POLICY_NOT_FOUND: 404,
    ErrorCode.VERIFICATION_FAILED: 401,
    ErrorCode.VERIFICATION_LOCKED: 423,
    ErrorCode.VERIFICATION_REQUIRED: 401,
    ErrorCode.TOKEN_SCOPE_MISMATCH: 403,
    ErrorCode.POLICY_NOT_ACTIVE: 409,
    ErrorCode.AMOUNT_EXCEEDS_PREMIUM: 409,
    ErrorCode.REFUND_ALREADY_OPEN: 409,
    ErrorCode.IDEMPOTENCY_KEY_CONFLICT: 409,
    ErrorCode.HOLDER_NAME_MISMATCH: 403,
    ErrorCode.SAME_ACCOUNT: 409,
    ErrorCode.ROUTE_NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.HTTP_ERROR: 400,
    ErrorCode.INTERNAL_ERROR: 500,
}


class DomainError(Exception):
    """A business rule said no. Always rendered as a REJECTED envelope."""

    def __init__(self, code: ErrorCode, message: str, *, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}
        self.http_status = HTTP_STATUS[code]
