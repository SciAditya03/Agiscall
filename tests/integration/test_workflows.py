from app.workflows import WORKFLOWS, Step


def test_supported_requests():
    assert set(WORKFLOWS) == {"CHECK_POLICY_STATUS", "REQUEST_REFUND", "UPDATE_BANK_ACCOUNT"}


def test_verification_step_matches_flag():
    for workflow in WORKFLOWS.values():
        assert (Step.VERIFY in workflow.steps) == workflow.requires_verification, workflow.key


def test_every_workflow_starts_with_identify_and_ends_done():
    for workflow in WORKFLOWS.values():
        assert workflow.steps[0] == Step.IDENTIFY
        assert workflow.steps[-1] == Step.DONE


def test_required_fields():
    assert WORKFLOWS["CHECK_POLICY_STATUS"].required_fields == ("policy_id",)
    assert WORKFLOWS["REQUEST_REFUND"].required_fields == ("policy_id", "amount", "reason")
    assert WORKFLOWS["UPDATE_BANK_ACCOUNT"].required_fields == ("holder_name", "account_number", "ifsc")
