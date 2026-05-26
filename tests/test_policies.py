import pytest
from dasc.kernel import Kernel
from dasc.schemas import Intent
from dasc.policies import cybersecurity_policy, finance_policy, healthcare_policy, privacy_policy

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

def test_healthcare_policy_baa_check():
    kernel = Kernel()
    kernel.register_policy(healthcare_policy)
    
    # Sharing without BAA triggers REJECT
    intent = Intent(
        intent_id="H4",
        actor_agent="agent",
        action_type="SHARE",
        target_artifact="ehr",
        risk_tier=2,
        payload={"share_with_third_party": True, "has_active_baa": False}
    )
    decision = kernel.evaluate(intent)
    assert decision.status == "REJECT"
    assert "HIPAA_BAA_REQUIRED" in decision.reason_codes[0]

def test_privacy_policy_gdpr_checks():
    kernel = Kernel()
    kernel.register_policy(privacy_policy)
    
    # 1. GDPR Consent Check
    intent_consent = Intent(
        intent_id="P1",
        actor_agent="sync-bot",
        action_type="SYNC",
        target_artifact="user_db",
        risk_tier=2,
        payload={"user_residency": "EU", "contains_personal_data": True, "consent_obtained": False}
    )
    dec1 = kernel.evaluate(intent_consent)
    assert dec1.status == "REJECT"
    assert "GDPR_CONSENT_REQUIRED" in dec1.reason_codes[0]

    # 2. GDPR Sovereignty Check
    intent_sov = Intent(
        intent_id="P2",
        actor_agent="sync-bot",
        action_type="SYNC",
        target_artifact="user_db",
        risk_tier=2,
        payload={"user_residency": "EU", "target_region": "US", "has_scc": False}
    )
    dec2 = kernel.evaluate(intent_sov)
    assert dec2.status == "REJECT"
    assert "GDPR_SOVEREIGNTY_VIOLATION" in dec2.reason_codes[0]

    # 3. GDPR Child Protection Check
    intent_minor = Intent(
        intent_id="P3",
        actor_agent="reg-bot",
        action_type="REGISTER",
        target_artifact="user_db",
        risk_tier=1,
        payload={"user_age": 14, "parental_consent_verified": False}
    )
    dec3 = kernel.evaluate(intent_minor)
    assert dec3.status == "REJECT"
    assert "GDPR_CHILD_PROTECTION" in dec3.reason_codes[0]

    # 4. Right to be Forgotten Purge Check
    intent_purge = Intent(
        intent_id="P4",
        actor_agent="junior-agent",
        action_type="PURGE_USER_DATA",
        target_artifact="user_db",
        risk_tier=2
    )
    dec4 = kernel.evaluate(intent_purge)
    assert dec4.status == "REJECT"
    assert "PRIVILEGE_MISMATCH" in dec4.reason_codes[0]

def test_declarative_rules_directory_loading():
    import tempfile
    import os
    import json
    from dasc.policies.declarative import DeclarativePolicyEngine
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write first rule file
        rule1 = {
            "rules": [
                {
                    "name": "Limit Low spends",
                    "condition": "payload.amount > 100",
                    "action": "REJECT",
                    "reason": "TOO_EXPENSIVE_LOW"
                }
            ]
        }
        with open(os.path.join(tmpdir, "rule1.json"), "w") as f:
            json.dump(rule1, f)
            
        # Write second rule file
        rule2 = {
            "rules": [
                {
                    "name": "Block Admin actions",
                    "condition": "action_type == 'ADMIN_ACTION'",
                    "action": "REJECT",
                    "reason": "NO_ADMIN_ALLOWED"
                }
            ]
        }
        with open(os.path.join(tmpdir, "rule2.json"), "w") as f:
            json.dump(rule2, f)
            
        engine = DeclarativePolicyEngine()
        engine.load_rules_from_directory(tmpdir)
        
        kernel = Kernel()
        kernel.register_policy(engine.evaluate_policies)
        
        # Test rule 1
        intent1 = Intent(
            intent_id="T1",
            actor_agent="agent",
            action_type="transfer",
            target_artifact="bank",
            risk_tier=1,
            payload={"amount": 150}
        )
        dec1 = kernel.evaluate(intent1)
        assert dec1.status == "REJECT"
        assert "TOO_EXPENSIVE_LOW" in dec1.reason_codes[0]
        
        # Test rule 2
        intent2 = Intent(
            intent_id="T2",
            actor_agent="agent",
            action_type="ADMIN_ACTION",
            target_artifact="bank",
            risk_tier=1,
            payload={"amount": 50}
        )
        dec2 = kernel.evaluate(intent2)
        assert dec2.status == "REJECT"
        assert "NO_ADMIN_ALLOWED" in dec2.reason_codes[0]

def test_imperative_policies_directory_loading():
    import tempfile
    import os
    import sys
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dynamic python policy file
        policy_code = """
def custom_test_policy(intent):
    \"\"\"Dynamic policy for test execution\"\"\"
    payload = getattr(intent, 'payload', {}) or {}
    if payload.get('should_block'):
        return False, "DYNAMIC_BLOCK_TRIGGERED"
    return True, ""
"""
        with open(os.path.join(tmpdir, "my_custom_policy.py"), "w") as f:
            f.write(policy_code)
            
        kernel = Kernel()
        
        # Let's perform the dynamic import
        import importlib.util
        POLICIES_DIR = tmpdir
        for root_dir, _, files in os.walk(POLICIES_DIR):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root_dir, file)
                    module_name = f"dasc_dynamic_policy_test_{os.path.splitext(file)[0]}"
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if callable(attr) and attr_name.endswith("_policy"):
                                kernel.register_policy(attr)
                                
        # Test registered dynamic policy
        intent_block = Intent(
            intent_id="TI1",
            actor_agent="agent",
            action_type="do_something",
            target_artifact="any",
            risk_tier=1,
            payload={"should_block": True}
        )
        dec_block = kernel.evaluate(intent_block)
        assert dec_block.status == "REJECT"
        assert "DYNAMIC_BLOCK_TRIGGERED" in dec_block.reason_codes[0]

        intent_pass = Intent(
            intent_id="TI2",
            actor_agent="agent",
            action_type="do_something",
            target_artifact="any",
            risk_tier=1,
            payload={"should_block": False}
        )
        dec_pass = kernel.evaluate(intent_pass)
        assert dec_pass.status == "COMMIT"

def test_declarative_rules_new_verticals():
    from dasc.policies.declarative import DeclarativePolicyEngine
    
    rules = {
        "rules": [
            {
                "name": "Database Exfiltration Guard",
                "condition": "target_artifact in ['database', 'backup'] and action_type == 'READ' and actor_agent != 'security-agent'",
                "action": "ESCALATE",
                "reason": "SECURITY_EXFILTRATION_OVERWATCH"
            },
            {
                "name": "CCPA Data Deletion Gate",
                "condition": "action_type == 'DELETE_CUSTOMER_DATA' and payload.ccpa_verified == false",
                "action": "REJECT",
                "reason": "CCPA_COMPLIANCE"
            },
            {
                "name": "CRM Bulk Export Guard",
                "condition": "action_type == 'EXPORT_CRM_CONTACTS' and payload.record_count > 100",
                "action": "ESCALATE",
                "reason": "CRM_DATA_LEAK_PREVENTION"
            },
            {
                "name": "Supply Chain Order Limit",
                "condition": "action_type == 'PLACE_PURCHASE_ORDER' and payload.total_cost > 50000",
                "action": "ESCALATE",
                "reason": "SUPPLY_CHAIN_LIMIT"
            }
        ]
    }
    
    engine = DeclarativePolicyEngine(rules_json=rules)
    kernel = Kernel()
    kernel.register_policy(engine.evaluate_policies)
    
    # 1. Security check - normal read should commit
    intent_sec_pass = Intent(
        intent_id="S1", actor_agent="standard-agent", action_type="READ", target_artifact="file.txt", risk_tier=1
    )
    assert kernel.evaluate(intent_sec_pass).status == "COMMIT"
    
    # DB read by non-security agent should escalate
    intent_sec_fail = Intent(
        intent_id="S2", actor_agent="standard-agent", action_type="READ", target_artifact="database", risk_tier=1
    )
    assert kernel.evaluate(intent_sec_fail).status == "ESCALATE"
    
    # 2. CCPA Check - unverified CCPA should reject
    intent_ccpa_fail = Intent(
        intent_id="L1", actor_agent="compliance-agent", action_type="DELETE_CUSTOMER_DATA", target_artifact="crm", risk_tier=2,
        payload={"ccpa_verified": False}
    )
    assert kernel.evaluate(intent_ccpa_fail).status == "REJECT"
    
    # 3. CRM check - high record count should escalate
    intent_crm_fail = Intent(
        intent_id="C1", actor_agent="crm-bot", action_type="EXPORT_CRM_CONTACTS", target_artifact="contacts", risk_tier=2,
        payload={"record_count": 150}
    )
    assert kernel.evaluate(intent_crm_fail).status == "ESCALATE"
    
    # 4. Supply Chain check - high cost order should escalate
    intent_sc_fail = Intent(
        intent_id="SC1", actor_agent="procurement-bot", action_type="PLACE_PURCHASE_ORDER", target_artifact="vendor_db", risk_tier=2,
        payload={"total_cost": 60000}
    )
    assert kernel.evaluate(intent_sc_fail).status == "ESCALATE"

