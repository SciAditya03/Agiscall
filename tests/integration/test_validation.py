from decimal import Decimal

import pytest

from app import validation as v


@pytest.mark.parametrize("raw", ["pol 3001", "POL3001", " pol-3001 ", "POL - 3001", "pol_3001"])
def test_normalize_id_handles_spoken_forms(raw):
    assert v.normalize_id(raw) == "POL-3001"


def test_normalize_id_keeps_unusual_ids_uppercased_without_spaces():
    assert v.normalize_id(" ab12cd ") == "AB12CD"


def test_normalize_id_rejects_blank():
    with pytest.raises(ValueError, match="cannot be empty"):
        v.normalize_id("   ")


def test_clean_lookup_id_returns_empty_for_blank():
    assert v.clean_lookup_id("  ") == ""
    assert v.clean_lookup_id("cust1001") == "CUST-1001"


def test_normalize_text_collapses_whitespace_and_rejects_blank():
    assert v.normalize_text("  Priya    Sharma ") == "Priya Sharma"
    with pytest.raises(ValueError, match="cannot be empty"):
        v.normalize_text(" \t ")


@pytest.mark.parametrize("raw", ["1200", "1200.5", "1200.50", "0.01", "1200.500"])
def test_validate_amount_accepts(raw):
    assert v.validate_amount(Decimal(raw)) == Decimal(raw)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("0", "greater than zero"),
        ("-5", "greater than zero"),
        ("10.001", "two decimal places"),
        ("NaN", "must be a number"),
        ("Infinity", "must be a number"),
    ],
)
def test_validate_amount_rejects(raw, message):
    with pytest.raises(ValueError, match=message):
        v.validate_amount(Decimal(raw))


def test_normalize_reason():
    assert v.normalize_reason("  duplicate   premium charge ") == "duplicate premium charge"
    with pytest.raises(ValueError, match="between 3 and 500"):
        v.normalize_reason("no")
    with pytest.raises(ValueError, match="between 3 and 500"):
        v.normalize_reason("x" * 501)


def test_normalize_account_number():
    assert v.normalize_account_number("5010 0234 5678 90") == "50100234567890"
    for bad in ["12345678", "1" * 19, "5010-0234-5678", "abcdefghij", "५०१००२३४५६७८"]:
        with pytest.raises(ValueError, match="9 to 18 digits"):
            v.normalize_account_number(bad)


def test_normalize_ifsc():
    assert v.normalize_ifsc("hdfc 000 1234") == "HDFC0001234"
    for bad in ["HDFC1001234", "HDF0001234", "HDFC00012345", ""]:
        with pytest.raises(ValueError, match="HDFC0001234"):
            v.normalize_ifsc(bad)


def test_names_match_ignores_case_and_spacing():
    assert v.names_match("  priya   SHARMA ", "Priya Sharma")
    assert not v.names_match("Rahul Mehta", "Priya Sharma")


def test_masking():
    assert v.mask_account("50100234567890") == "XXXXXX7890"
    assert v.mask_phone("+91 98765 43210") == "XXXXXX3210"
    assert v.mask_email("priya.sharma@example.com") == "p****@example.com"
    assert v.mask_email("not-an-email") == "****"


def test_format_inr():
    assert v.format_inr(Decimal("1200")) == "₹1,200.00"
    assert v.format_inr(Decimal("18000.5")) == "₹18,000.50"
