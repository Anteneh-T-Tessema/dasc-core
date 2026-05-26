from dasc import Kernel, Intent, Evidence
import re

# --- 1. CYBERSECURITY POLICY ---
def shell_injection_policy(intent: Intent):
    """
    Blocks run_command intents if they contain dangerous shell operators.
    """
    if intent.action_type == "run_command":
        command = intent.target_artifact
        restricted_operators = [";", "|", "&&", ">", "`", "$(", "bash"]
        for op in restricted_operators:
            if op in command:
                return False, f"Shell injection risk: Found restricted operator '{op}'"
    return True, ""

# --- 2. FINANCE POLICY (Two-Agent Rule) ---
def dual_approval_policy(intent: Intent):
    """
    Enforces that high-value transactions must have evidence from 
    both a Requester and an Approver.
    """
    if intent.action_type == "transfer_funds" and intent.risk_tier >= 3:
        sources = [ev.source_type for ev in intent.evidence]
        if "requester" not in sources or "approver" not in sources:
            return False, "Dual-Approval Violation: Missing 'requester' or 'approver' signature"
    return True, ""

# --- 3. HEALTHCARE POLICY (Clinical Evidence) ---
def clinical_governance_policy(intent: Intent):
    """
    Requires a 'doctor_signature' for any medication changes.
    """
    if intent.action_type == "change_medication":
        has_signature = any(ev.source_type == "doctor_signature" for ev in intent.evidence)
        if not has_signature:
            return False, "Clinical Violation: Medication change requires doctor_signature"
    return True, ""

# --- SHOWCASE EXECUTION ---
if __name__ == "__main__":
    kernel = Kernel()
    kernel.register_policy(shell_injection_policy)
    kernel.register_policy(dual_approval_policy)
    kernel.register_policy(clinical_governance_policy)

    print("=== DASC INDUSTRY SHOWCASE ===\n")

    # TEST CYBERSECURITY
    malicious_intent = Intent(
        intent_id="CYBER-001",
        actor_agent="dev_agent",
        action_type="run_command",
        target_artifact="ls -l /tmp | bash", # Dangerous!
        risk_tier=2
    )
    res = kernel.evaluate(malicious_intent)
    print(f"Cybersecurity Result: {res.status} - {res.reason_codes}\n")

    # TEST FINANCE
    money_intent = Intent(
        intent_id="FIN-001",
        actor_agent="payment_agent",
        action_type="transfer_funds",
        target_artifact="ACC_456",
        risk_tier=3,
        compensation_plan={"action": "reverse"},
        evidence=[Evidence(evidence_id="E1", source_type="requester", content="Request ID 789", span={"line": 10})]
        # Missing Approver!
    )
    res = kernel.evaluate(money_intent)
    print(f"Finance Result: {res.status} - {res.reason_codes}\n")

    # TEST HEALTHCARE
    med_intent = Intent(
        intent_id="HLTH-001",
        actor_agent="nurse_agent",
        action_type="change_medication",
        target_artifact="PATIENT_999",
        risk_tier=2,
        evidence=[Evidence(evidence_id="E2", source_type="nurse_observation", content="Patient is stable", span={"line": 42})]
        # Missing Doctor!
    )
    res = kernel.evaluate(med_intent)
    print(f"Healthcare Result: {res.status} - {res.reason_codes}\n")

    # TEST VALID TRANSACTION
    valid_intent = Intent(
        intent_id="FIN-002",
        actor_agent="payment_agent",
        action_type="transfer_funds",
        target_artifact="ACC_456",
        risk_tier=3,
        compensation_plan={"action": "reverse"},
        evidence=[
            Evidence(evidence_id="E3", source_type="requester", content="Request ID 789", span={"line": 10}),
            Evidence(evidence_id="E4", source_type="approver", content="Approved by Admin", span={"line": 11})
        ]
    )
    res = kernel.evaluate(valid_intent)
    print(f"Valid Transaction Result: {res.status}")
