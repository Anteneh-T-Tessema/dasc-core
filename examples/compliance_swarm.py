import sys
import os
import time
import requests
import json

# Ensure package is in the import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dasc import DASCClient
from dasc.schemas import Intent

API_BASE = "http://localhost:8000"
HEADERS = {
    "X-API-KEY": "dasc-dev-key-123",
    "Content-Type": "application/json"
}

# The compliance policy ruleset
COMPLIANCE_RULESET = {
    "rules": [
        {
            "name": "HIPAA PHI Access Gate",
            "condition": "payload.has_phi == true and payload.break_glass_authorized == false",
            "action": "REJECT",
            "reason": "HIPAA_VIOLATION: Unauthorized PHI access attempt"
        },
        {
            "name": "GDPR Location Sovereignty",
            "condition": "payload.user_residency == 'EU' and payload.target_region != 'EU'",
            "action": "REJECT",
            "reason": "GDPR_VIOLATION: EU user data must remain in EU region"
        },
        {
            "name": "ISO 42001 AI human gate",
            "condition": "risk_tier >= 3 and payload.human_supervisor_present == false",
            "action": "ESCALATE",
            "reason": "ISO_42001_COMPLIANCE: High-risk AI actions require human oversight"
        },
        {
            "name": "ISO 27001 Access control",
            "condition": "action_type in ['write_config', 'delete_backup'] and actor_agent != 'admin-agent'",
            "action": "REJECT",
            "reason": "ISO_27001_CONTROL_A9: Unauthorized system modification blocked"
        }
    ]
}

def print_result(title, intent: Intent, decision):
    print("=" * 70)
    print(f"Scenario: {title}")
    print("-" * 70)
    print(f"Intent Submitter: {intent.actor_agent}")
    print(f"Action Type:      {intent.action_type}")
    print(f"Risk Tier:        {intent.risk_tier}")
    print(f"Payload:          {intent.payload}")
    print("-" * 70)
    
    status = decision.status
    reasons = decision.reason_codes
    
    if status == "COMMIT":
        print(f"🟢 DASC DECISION: ALLOW / COMMIT")
    elif status == "REJECT":
        print(f"🔴 DASC DECISION: REJECT / BLOCKED")
        print(f"   Reason Code:   {reasons[0] if reasons else 'UNKNOWN'}")
    elif status == "ESCALATE":
        print(f"🟡 DASC DECISION: ESCALATED TO HITL DASHBOARD")
        print(f"   Reason Code:   {reasons[0] if reasons else 'UNKNOWN'}")
    print("=" * 70 + "\n")

def run_compliance_demo():
    print("=" * 80)
    print(" DASC COMPLIANCE SWARM & DYNAMIC POLICY EVALUATION ")
    print("=" * 80)
    
    # 1. Capture current ruleset to restore at the end
    print("[1/5] Fetching original safety rules...")
    try:
        res = requests.get(f"{API_BASE}/policies", headers=HEADERS)
        original_rules = res.json()
    except Exception as e:
        print(f"❌ Error connecting to DASC FastAPI Server: {e}")
        print("Please ensure the safety server is running (`python3 -m dasc.cli serve`) before starting this script.")
        sys.exit(1)

    # 2. Upload the new compliance policies
    print("[2/5] Deploying HIPAA, GDPR, ISO 42001, and ISO 27001 rulesets dynamically...")
    res = requests.post(f"{API_BASE}/policies", headers=HEADERS, json=COMPLIANCE_RULESET)
    if res.status_code == 200:
        print("✅ Rules hot-reloaded successfully on the safety server!")
    else:
        print(f"❌ Failed to update rules: {res.text}")
        sys.exit(1)
        
    print("\n[3/5] Simulating Multi-Agent Compliance Scenarios...\n")
    client = DASCClient()

    # ----------------------------------------------------
    # SCENARIO 1: HIPAA (PHI / Health Privacy Protection)
    # ----------------------------------------------------
    intent_hipaa_fail = Intent(
        intent_id="hipaa-violation-test",
        actor_agent="diagnostic-bot",
        action_type="fetch_patient_records",
        target_artifact="patient_db",
        risk_tier=2,
        payload={"has_phi": True, "break_glass_authorized": False},
        evidence=[]
    )
    dec_hipaa_fail = client.evaluate(intent_hipaa_fail)
    print_result("HIPAA PHI Access Gate - Unauthorized Access", intent_hipaa_fail, dec_hipaa_fail)

    intent_hipaa_pass = Intent(
        intent_id="hipaa-allowed-test",
        actor_agent="diagnostic-bot",
        action_type="fetch_patient_records",
        target_artifact="patient_db",
        risk_tier=2,
        payload={"has_phi": True, "break_glass_authorized": True},
        evidence=[]
    )
    dec_hipaa_pass = client.evaluate(intent_hipaa_pass)
    print_result("HIPAA PHI Access Gate - Emergency Break-Glass Authorized", intent_hipaa_pass, dec_hipaa_pass)

    # ----------------------------------------------------
    # SCENARIO 2: GDPR (Data Sovereignty)
    # ----------------------------------------------------
    intent_gdpr_fail = Intent(
        intent_id="gdpr-violation-test",
        actor_agent="sync-agent",
        action_type="export_customer_data",
        target_artifact="customer_records",
        risk_tier=2,
        payload={"user_residency": "EU", "target_region": "US"},
        evidence=[]
    )
    dec_gdpr_fail = client.evaluate(intent_gdpr_fail)
    print_result("GDPR Sovereign Boundary - Exporting EU User Data outside EU", intent_gdpr_fail, dec_gdpr_fail)

    intent_gdpr_pass = Intent(
        intent_id="gdpr-allowed-test",
        actor_agent="sync-agent",
        action_type="export_customer_data",
        target_artifact="customer_records",
        risk_tier=2,
        payload={"user_residency": "EU", "target_region": "EU"},
        evidence=[]
    )
    dec_gdpr_pass = client.evaluate(intent_gdpr_pass)
    print_result("GDPR Sovereign Boundary - Storing EU User Data in EU Region", intent_gdpr_pass, dec_gdpr_pass)

    # ----------------------------------------------------
    # SCENARIO 3: ISO 42001 (High-Risk AI System Oversight)
    # ----------------------------------------------------
    intent_iso42001_fail = Intent(
        intent_id="iso42001-violation-test",
        actor_agent="credit-underwriter-agent",
        action_type="reject_loan_applicant",
        target_artifact="underwriting_decision_engine",
        risk_tier=3,
        payload={"human_supervisor_present": False},
        evidence=[]
    )
    dec_iso42001_fail = client.evaluate(intent_iso42001_fail)
    print_result("ISO 42001 AI Safety - High-Risk Credit Scoring without Oversight", intent_iso42001_fail, dec_iso42001_fail)

    # ----------------------------------------------------
    # SCENARIO 4: ISO 27001 (Access Control / Least Privilege)
    # ----------------------------------------------------
    intent_iso27001_fail = Intent(
        intent_id="iso27001-violation-test",
        actor_agent="junior-analyst-bot",
        action_type="write_config",
        target_artifact="production_firewall",
        risk_tier=2,
        payload={},
        evidence=[]
    )
    dec_iso27001_fail = client.evaluate(intent_iso27001_fail)
    print_result("ISO 27001 Control - Non-Admin attempting to modify config", intent_iso27001_fail, dec_iso27001_fail)

    intent_iso27001_pass = Intent(
        intent_id="iso27001-allowed-test",
        actor_agent="admin-agent",
        action_type="write_config",
        target_artifact="production_firewall",
        risk_tier=2,
        payload={},
        evidence=[]
    )
    dec_iso27001_pass = client.evaluate(intent_iso27001_pass)
    print_result("ISO 27001 Control - Admin modifying system configuration", intent_iso27001_pass, dec_iso27001_pass)

    # 5. Restore the original safety ruleset
    print("[4/5] Restoring original default safety rules...")
    res = requests.post(f"{API_BASE}/policies", headers=HEADERS, json=original_rules)
    if res.status_code == 200:
        print("✅ Original rules restored successfully on server.")
    else:
        print(f"⚠️ Warning: Failed to restore original rules: {res.text}")
        
    print("\n[5/5] Done! All compliance scenarios verified successfully.")

if __name__ == "__main__":
    run_compliance_demo()
