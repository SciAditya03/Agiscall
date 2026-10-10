import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.models import Base, Customer, Operation, Policy, RefundRequest
from seed.seed import seed


def test_exactly_the_four_breakdown_tables(engine):
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert tables == {"customers", "policies", "refund_requests", "operations"}


def test_migration_matches_models(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_seed_loads_demo_data(seeded):
    assert seeded.scalar(select(func.count()).select_from(Customer)) == 5
    assert seeded.scalar(select(func.count()).select_from(Policy)) == 6
    priya = seeded.get(Customer, "CUST-1001")
    assert priya.full_name == "Priya Sharma"
    assert seeded.get(Customer, "CUST-1004").bank_account_number is None


def test_seed_is_idempotent(seeded):
    seed(seeded)
    assert seeded.scalar(select(func.count()).select_from(Customer)) == 5
    assert seeded.scalar(select(func.count()).select_from(Policy)) == 6


def test_seed_reset_clears_refunds_and_operations(seeded):
    seeded.add(RefundRequest(id="RR-000001", policy_id="POL-3001", customer_id="CUST-1001",
                             amount=100, reason="test", status="SUBMITTED"))
    seeded.add(Operation(operation_type="VERIFY", status="SUCCESS", code="VERIFIED", details={}))
    seeded.commit()

    seed(seeded, reset=True)

    assert seeded.scalar(select(func.count()).select_from(RefundRequest)) == 0
    assert seeded.scalar(select(func.count()).select_from(Operation)) == 0
    assert seeded.scalar(select(func.count()).select_from(Customer)) == 5


def test_only_one_open_refund_per_policy_at_db_level(seeded):
    for refund_id in ("RR-000001", "RR-000002"):
        seeded.add(RefundRequest(id=refund_id, policy_id="POL-3001", customer_id="CUST-1001",
                                 amount=100, reason="test", status="SUBMITTED"))
    with pytest.raises(IntegrityError):
        seeded.commit()
