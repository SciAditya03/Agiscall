"""Supported customer requests and the steps each one goes through.

The conversation service (Person 1) tracks which step a call is on. This module is the
shared definition of what each request needs before this API can act on it.
"""
from dataclasses import dataclass
from enum import StrEnum


class Step(StrEnum):
    IDENTIFY = "IDENTIFY"
    VERIFY = "VERIFY"
    COLLECT = "COLLECT"
    EXECUTE = "EXECUTE"
    DONE = "DONE"


@dataclass(frozen=True)
class Workflow:
    key: str
    description: str
    endpoint: str
    requires_verification: bool
    required_fields: tuple[str, ...]
    steps: tuple[Step, ...]


_VERIFIED_STEPS = (Step.IDENTIFY, Step.VERIFY, Step.COLLECT, Step.EXECUTE, Step.DONE)

WORKFLOWS: dict[str, Workflow] = {
    workflow.key: workflow
    for workflow in (
        Workflow(
            key="CHECK_POLICY_STATUS",
            description="Tell the caller the status of one of their policies.",
            endpoint="GET /policies/{policy_id}",
            requires_verification=False,
            required_fields=("policy_id",),
            steps=(Step.IDENTIFY, Step.DONE),
        ),
        Workflow(
            key="REQUEST_REFUND",
            description="Raise a premium refund request on an active policy.",
            endpoint="POST /refund-requests",
            requires_verification=True,
            required_fields=("policy_id", "amount", "reason"),
            steps=_VERIFIED_STEPS,
        ),
        Workflow(
            key="UPDATE_BANK_ACCOUNT",
            description="Change the bank account refunds are paid into.",
            endpoint="PATCH /customers/{customer_id}/bank-account",
            requires_verification=True,
            required_fields=("holder_name", "account_number", "ifsc"),
            steps=_VERIFIED_STEPS,
        ),
    )
}
