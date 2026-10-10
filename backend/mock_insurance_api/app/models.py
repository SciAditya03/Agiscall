"""Database tables: exactly the four named in Breakdown.md."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

REFUND_OPEN_STATUSES = ("SUBMITTED",)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    date_of_birth: Mapped[date] = mapped_column(Date)
    phone: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    bank_holder_name: Mapped[str | None] = mapped_column(Text)
    bank_account_number: Mapped[str | None] = mapped_column(Text)
    bank_ifsc: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (Index("ix_policies_customer_id", "customer_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    customer_id: Mapped[str] = mapped_column(Text, ForeignKey("customers.id"))
    product_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    premium_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)


class RefundRequest(Base):
    __tablename__ = "refund_requests"
    __table_args__ = (
        Index("ix_refund_requests_customer_id", "customer_id"),
        # Backs up the "one open refund per policy" rule against concurrent requests.
        Index(
            "uq_refund_requests_one_open_per_policy",
            "policy_id",
            unique=True,
            postgresql_where=text("status = 'SUBMITTED'"),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    policy_id: Mapped[str] = mapped_column(Text, ForeignKey("policies.id"))
    customer_id: Mapped[str] = mapped_column(Text, ForeignKey("customers.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Operation(Base):
    """The breakdown's "simulated-operation" table, used as the audit log."""

    __tablename__ = "operations"
    __table_args__ = (
        Index("ix_operations_customer_type_created", "customer_id", "operation_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operation_type: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
