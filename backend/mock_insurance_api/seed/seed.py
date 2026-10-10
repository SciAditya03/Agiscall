"""Demo customers and policies. Safe to run repeatedly.

    python -m seed.seed            # upsert customers + policies
    python -m seed.seed --reset    # also clear refund requests and the operations log
"""
import argparse
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import Customer, Policy

CUSTOMERS = [
    dict(id="CUST-1001", full_name="Priya Sharma", date_of_birth=date(1990, 4, 12),
         phone="+919876543210", email="priya.sharma@example.com",
         bank_holder_name="Priya Sharma", bank_account_number="50100234567890", bank_ifsc="HDFC0001234"),
    dict(id="CUST-1002", full_name="Arjun Nair", date_of_birth=date(1985, 11, 2),
         phone="+919812345678", email="arjun.nair@example.com",
         bank_holder_name="Arjun Nair", bank_account_number="917010045678123", bank_ifsc="UTIB0000123"),
    dict(id="CUST-1003", full_name="Meera Iyer", date_of_birth=date(1978, 1, 25),
         phone="+919845012345", email="meera.iyer@example.com",
         bank_holder_name="Meera Iyer", bank_account_number="00011234567", bank_ifsc="SBIN0001234"),
    dict(id="CUST-1004", full_name="Rohan Gupta", date_of_birth=date(1995, 7, 30),
         phone="+919900112233", email="rohan.gupta@example.com",
         bank_holder_name=None, bank_account_number=None, bank_ifsc=None),
    dict(id="CUST-1005", full_name="Ananya Reddy", date_of_birth=date(2000, 3, 8),
         phone="+919700998877", email="ananya.reddy@example.com",
         bank_holder_name="Ananya Reddy", bank_account_number="123456789012", bank_ifsc="ICIC0000456"),
]

POLICIES = [
    dict(id="POL-3001", customer_id="CUST-1001", product_type="HEALTH", status="ACTIVE",
         premium_amount=Decimal("18000.00"), sum_insured=Decimal("500000.00"),
         start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)),
    dict(id="POL-3002", customer_id="CUST-1002", product_type="MOTOR", status="LAPSED",
         premium_amount=Decimal("9500.00"), sum_insured=Decimal("300000.00"),
         start_date=date(2025, 3, 1), end_date=date(2026, 2, 28)),
    dict(id="POL-3003", customer_id="CUST-1003", product_type="LIFE", status="ACTIVE",
         premium_amount=Decimal("24000.00"), sum_insured=Decimal("2500000.00"),
         start_date=date(2020, 6, 1), end_date=date(2045, 5, 31)),
    dict(id="POL-3004", customer_id="CUST-1003", product_type="HEALTH", status="ACTIVE",
         premium_amount=Decimal("12000.00"), sum_insured=Decimal("300000.00"),
         start_date=date(2026, 4, 1), end_date=date(2027, 3, 31)),
    dict(id="POL-3005", customer_id="CUST-1004", product_type="MOTOR", status="ACTIVE",
         premium_amount=Decimal("7200.00"), sum_insured=Decimal("450000.00"),
         start_date=date(2026, 2, 15), end_date=date(2027, 2, 14)),
    dict(id="POL-3006", customer_id="CUST-1005", product_type="HEALTH", status="CANCELLED",
         premium_amount=Decimal("10000.00"), sum_insured=Decimal("300000.00"),
         start_date=date(2025, 9, 1), end_date=date(2026, 8, 31)),
]


def seed(session: Session, *, reset: bool = False) -> None:
    if reset:
        session.execute(text("TRUNCATE operations, refund_requests RESTART IDENTITY"))
    for row in CUSTOMERS:
        session.merge(Customer(**row))
    session.flush()
    for row in POLICIES:
        session.merge(Policy(**row))
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load AegisCall demo customers and policies.")
    parser.add_argument("--reset", action="store_true", help="also clear refund requests and the operations log")
    args = parser.parse_args()
    with Session(get_engine()) as session:
        seed(session, reset=args.reset)
    print(f"Seeded {len(CUSTOMERS)} customers and {len(POLICIES)} policies.")


if __name__ == "__main__":
    main()
