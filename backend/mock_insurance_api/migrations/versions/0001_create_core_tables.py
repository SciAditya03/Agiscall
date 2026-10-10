"""create core tables

Revision ID: 0001
Revises:
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("bank_holder_name", sa.Text(), nullable=True),
        sa.Column("bank_account_number", sa.Text(), nullable=True),
        sa.Column("bank_ifsc", sa.Text(), nullable=True),
        _timestamp("created_at"),
        _timestamp("updated_at"),
    )
    op.create_table(
        "policies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("customer_id", sa.Text(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("product_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("premium_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("sum_insured", sa.Numeric(14, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
    )
    op.create_index("ix_policies_customer_id", "policies", ["customer_id"])
    op.create_table(
        "refund_requests",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("policy_id", sa.Text(), sa.ForeignKey("policies.id"), nullable=False),
        sa.Column("customer_id", sa.Text(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True, unique=True),
        _timestamp("created_at"),
    )
    op.create_index("ix_refund_requests_customer_id", "refund_requests", ["customer_id"])
    op.create_index(
        "uq_refund_requests_one_open_per_policy",
        "refund_requests",
        ["policy_id"],
        unique=True,
        postgresql_where=sa.text("status = 'SUBMITTED'"),
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        _timestamp("created_at"),
    )
    op.create_index(
        "ix_operations_customer_type_created",
        "operations",
        ["customer_id", "operation_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("operations")
    op.drop_table("refund_requests")
    op.drop_table("policies")
    op.drop_table("customers")
