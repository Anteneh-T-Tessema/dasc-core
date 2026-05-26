import json
from ..schemas import Intent

def privacy_policy(intent: Intent):
    """
    Privacy Policy (GDPR / Data Minimization / Sovereignty)
    Focuses on GDPR consent requirements, sovereignty borders, parental consent, and right to be forgotten (purge actions).
    """
    payload = getattr(intent, "payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}

    # 1. GDPR Consent Check: If processing personal data for an EU resident, consent is mandatory
    if payload.get("user_residency") == "EU" and payload.get("contains_personal_data"):
        if not payload.get("consent_obtained"):
            return False, "GDPR_CONSENT_REQUIRED: Processing personal data of EU residents requires explicit user consent"

    # 2. GDPR Data Sovereignty: EU user records must not leave the EU region unless standard contractual clauses (SCC) are present
    if payload.get("user_residency") == "EU" and payload.get("target_region") and payload.get("target_region") != "EU":
        if not payload.get("has_scc"):
            return False, "GDPR_SOVEREIGNTY_VIOLATION: Transborder flow of EU personal data outside EU requires Standard Contractual Clauses (SCC)"

    # 3. Child Protection (GDPR / COPPA): Users under 16 require parent consent for data handling
    if payload.get("user_age") and isinstance(payload["user_age"], (int, float)) and payload["user_age"] < 16:
        if not payload.get("parental_consent_verified"):
            return False, "GDPR_CHILD_PROTECTION: Handling data of minors under 16 requires verified parental consent"

    # 4. Right to be Forgotten (Purging): Only authorized agents can perform hard purges of user records
    if intent.action_type == "PURGE_USER_DATA":
        if "compliance" not in intent.actor_agent.lower() and "admin" not in intent.actor_agent.lower():
            return False, "PRIVILEGE_MISMATCH: Only compliance or admin agents are authorized to purge user databases"

    return True, ""
