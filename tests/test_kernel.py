import pytest
from dasc.kernel import Kernel
from dasc.schemas import Intent

def test_kernel_commit_valid_intent():
    kernel = Kernel(current_state_versions={"file.txt": "v1.0"})
    intent = Intent(
        intent_id="T1",
        actor_agent="agent",
        action_type="write",
        target_artifact="file.txt",
        risk_tier=1,
        state_version_vector={"file.txt": "v1.0"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "COMMIT"

def test_kernel_reject_occ_conflict():
    kernel = Kernel(current_state_versions={"file.txt": "v2.0"})
    intent = Intent(
        intent_id="T2",
        actor_agent="agent",
        action_type="write",
        target_artifact="file.txt",
        risk_tier=1,
        state_version_vector={"file.txt": "v1.0"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert any("OCC_CONFLICT" in r for r in decision.reason_codes)

def test_kernel_reject_high_risk_missing_plan():
    kernel = Kernel()
    intent = Intent(
        intent_id="T3",
        actor_agent="agent",
        action_type="delete",
        target_artifact="db",
        risk_tier=3
        # Missing compensation_plan
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK" in decision.reason_codes

def test_kernel_commit_high_risk_with_plan():
    kernel = Kernel()
    intent = Intent(
        intent_id="T4",
        actor_agent="agent",
        action_type="delete",
        target_artifact="db",
        risk_tier=3,
        compensation_plan={"revert": "restore_backup"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "COMMIT"

def test_kernel_reject_taint_check():
    from dasc.schemas import Evidence
    kernel = Kernel()
    intent = Intent(
        intent_id="T5",
        actor_agent="agent",
        action_type="write",
        target_artifact="sensitive_file",
        risk_tier=2,
        evidence=[Evidence(evidence_id="E1", source_type="untrusted", span={})]
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "IFC_TAINT_DETECTED" in decision.reason_codes[0]

def test_kernel_escalate_tier_4():
    kernel = Kernel()
    intent = Intent(
        intent_id="T6",
        actor_agent="agent",
        action_type="nuke",
        target_artifact="world",
        risk_tier=4,
        compensation_plan={"action": "recreate_world"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "ESCALATE"
    assert "TIER_4_MANDATORY_ESCALATION" in decision.reason_codes
