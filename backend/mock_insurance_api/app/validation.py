"""Pure validation, normalisation and masking helpers. No database access.

Validators raise ValueError with a sentence the voice agent can read back.
"""
import re
from decimal import Decimal

IFSC_PATTERN = re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")
ACCOUNT_PATTERN = re.compile(r"[0-9]{9,18}")
_ID_PATTERN = re.compile(r"([A-Z]+)[\s_-]*([0-9]+)")


def normalize_id(value: str) -> str:
    """'pol 3001', 'POL3001', ' pol-3001 ' -> 'POL-3001'."""
    compact = value.strip().upper()
    match = _ID_PATTERN.fullmatch(compact)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    cleaned = "".join(compact.split())
    if not cleaned:
        raise ValueError("This field cannot be empty")
    return cleaned


def clean_lookup_id(value: str) -> str:
    """Like normalize_id, but blank input gives '' so the lookup simply misses."""
    try:
        return normalize_id(value)
    except ValueError:
        return ""


def normalize_text(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("This field cannot be empty")
    return cleaned


def validate_amount(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("Amount must be a number")
    if value <= 0:
        raise ValueError("Amount must be greater than zero")
    if value.normalize().as_tuple().exponent < -2:
        raise ValueError("Amount can have at most two decimal places")
    return value


def normalize_reason(value: str) -> str:
    cleaned = " ".join(value.split())
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("Reason must be between 3 and 500 characters")
    return cleaned


def normalize_account_number(value: str) -> str:
    cleaned = "".join(value.split())
    if not ACCOUNT_PATTERN.fullmatch(cleaned):
        raise ValueError("Account number must be 9 to 18 digits")
    return cleaned


def normalize_ifsc(value: str) -> str:
    cleaned = "".join(value.split()).upper()
    if not IFSC_PATTERN.fullmatch(cleaned):
        raise ValueError("IFSC must look like HDFC0001234")
    return cleaned


def names_match(given: str, on_record: str) -> bool:
    return " ".join(given.split()).casefold() == " ".join(on_record.split()).casefold()


def mask_account(number: str) -> str:
    return "XXXXXX" + number[-4:]


def mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return "XXXXXX" + digits[-4:]


def mask_email(email: str) -> str:
    local, sep, domain = email.partition("@")
    if not sep or not local:
        return "****"
    return f"{local[0]}****@{domain}"


def format_inr(amount: Decimal) -> str:
    return f"₹{amount:,.2f}"
