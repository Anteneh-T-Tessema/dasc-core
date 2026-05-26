import pytest
from dasc.kernel import Kernel
from dasc.schemas import Intent
from dasc.policies import cybersecurity_policy, finance_policy, healthcare_policy

def test_cybersecurity_policy_dangerous_command():
    kernel = Kernel()
    kernel.register_policy(cybersecurity_policy)
    
    # 1. Test dangerous command
    intent = Intent(
        intent_id="C1",
        actor_agent="agent",
        action_type="EXEC",
        target_artifact="shell",
        risk_tier=2,
        payload={"command": "rm -rf /some/dir"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "DANGEROUS_COMMAND_DETECTED" in decision.reason_codes[0]

def test_cybersecurity_policy_restricted_path():
    kernel = Kernel()
    kernel.register_policy(cybersecurity_policy)
    
    intent = Intent(
        intent_id="C2",
        actor_agent="agent",
        action_type="READ",
        target_artifact="file",
        risk_tier=2,
        payload={"path": "/etc/passwd"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "RESTRICTED_PATH_ACCESS" in decision.reason_codes[0]

def test_cybersecurity_policy_privilege_mismatch():
    kernel = Kernel()
    kernel.register_policy(cybersecurity_policy)
    
    intent = Intent(
        intent_id="C3",
        actor_agent="untrusted-bot",
        action_type="WRITE",
        target_artifact="database",
        risk_tier=3,
        compensation_plan={"undo": "restore"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "PRIVILEGE_MISMATCH" in decision.reason_codes[0]

def test_finance_policy_spending_limit():
    kernel = Kernel()
    kernel.register_policy(finance_policy)
    
    # Spending limit exceeded for Tier < 4
    intent = Intent(
        intent_id="F1",
        actor_agent="agent",
        action_type="transfer",
        target_artifact="account",
        risk_tier=3,
        compensation_plan={"undo": "revert"},
        payload={"amount": 6000}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "TRANSACTION_LIMIT_EXCEEDED" in decision.reason_codes[0]

def test_finance_policy_unverified_recipient():
    kernel = Kernel()
    kernel.register_policy(finance_policy)
    
    intent = Intent(
        intent_id="F2",
        actor_agent="agent",
        action_type="TRANSFER",
        target_artifact="account",
        risk_tier=1,
        payload={"transaction_type": "TRANSFER", "recipient_verified": False}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "UNVERIFIED_RECIPIENT" in decision.reason_codes[0]

def test_finance_policy_crypto_restriction():
    kernel = Kernel()
    kernel.register_policy(finance_policy)
    
    intent = Intent(
        intent_id="F3",
        actor_agent="standard-agent",
        action_type="buy",
        target_artifact="wallet",
        risk_tier=1,
        payload={"currency": "BTC"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "CURRENCY_RESTRICTION" in decision.reason_codes[0]

def test_healthcare_policy_phi_detection():
    kernel = Kernel()
    kernel.register_policy(healthcare_policy)
    
    intent = Intent(
        intent_id="H1",
        actor_agent="agent",
        action_type="LOG",
        target_artifact="ehr",
        risk_tier=1,
        payload={"note": "Patient email: john@example.com"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "PHI_DETECTED" in decision.reason_codes[0]

def test_healthcare_policy_clinical_provenance():
    kernel = Kernel()
    kernel.register_policy(healthcare_policy)
    
    # Tier 3 requires EHR provenance_id
    intent = Intent(
        intent_id="H2",
        actor_agent="agent",
        action_type="DIAGNOSE",
        target_artifact="ehr",
        risk_tier=3,
        compensation_plan={"undo": "delete"},
        payload={"test": "xray"}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "MISSING_CLINICAL_PROVENANCE" in decision.reason_codes[0]

def test_healthcare_policy_controlled_substance():
    kernel = Kernel()
    kernel.register_policy(healthcare_policy)
    
    # Controlled substance requires break_glass_authorized
    intent = Intent(
        intent_id="H3",
        actor_agent="doctor-agent",
        action_type="MEDICATION_ORDER",
        target_artifact="ehr",
        risk_tier=2,
        payload={"is_controlled_substance": True, "break_glass_authorized": False}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "BREAK_GLASS_REQUIRED" in decision.reason_codes[0]

def test_declarative_policy_engine():
    from dasc.policies.declarative import DeclarativePolicyEngine
    
    rules = {
        "rules": [
            {
                "name": "block_big_spends",
                "condition": "payload.amount > 1000 and risk_tier < 3",
                "action": "REJECT",
                "reason": "TOO_EXPENSIVE"
            },
            {
                "name": "nuke_escalation",
                "condition": "action_type == 'NUKE'",
                "action": "ESCALATE",
                "reason": "NUKE_COMMAND_HITL"
            }
        ]
    }
    
    engine = DeclarativePolicyEngine(rules_json=rules)
    kernel = Kernel()
    kernel.register_policy(engine.evaluate_policies)
    
    # 1. Matches rule 1
    intent1 = Intent(
        intent_id="D1",
        actor_agent="agent",
        action_type="transfer",
        target_artifact="bank",
        risk_tier=1,
        payload={"amount": 1500}
    )
    dec1 = kernel.evaluate(intent1)
    assert dec1.status == "REJECT"
    assert "TOO_EXPENSIVE" in dec1.reason_codes[0]
    
    # 2. Does not match (risk_tier >= 3)
    intent2 = Intent(
        intent_id="D2",
        actor_agent="agent",
        action_type="transfer",
        target_artifact="bank",
        risk_tier=3,
        payload={"amount": 1500},
        compensation_plan={"undo": "reverse"}
    )
    dec2 = kernel.evaluate(intent2)
    assert dec2.status == "COMMIT"
    
    # 3. Matches rule 2 (escalation)
    intent3 = Intent(
        intent_id="D3",
        actor_agent="agent",
        action_type="NUKE",
        target_artifact="system",
        risk_tier=1
    )
    dec3 = kernel.evaluate(intent3)
    assert dec3.status == "ESCALATE"
    assert "NUKE_COMMAND_HITL" in dec3.reason_codes[0]
