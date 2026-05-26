import re
import json
from ..schemas import Intent

def healthcare_policy(intent: Intent):
    """
    Healthcare Policy (HIPAA & Clinical Safety)
    Focuses on HIPAA compliance, PHI/PII protection, clinical EHR provenance, and BAA requirements.
    """
    payload = getattr(intent, "payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}

    payload_str = json.dumps(payload)

    # 1. HIPAA Privacy: Scan for unmasked PHI (SSN, Email, MRN, Phone)
    phi_patterns = {
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "MRN": r"\bMRN-\d{4}-\d{4}\b",  # Medical Record Number
        "Phone": r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    }

    for name, pattern in phi_patterns.items():
        if re.search(pattern, payload_str):
            # Check if fields are explicitly masked or if encryption/tokenization is active
            if not payload.get("is_encrypted") and not payload.get("is_tokenized"):
                return False, f"PHI_DETECTED: Intent contains unmasked patient identifiable information ({name})"

    # 2. HIPAA Administrative: Enforce BAA (Business Associate Agreement) for external sharing
    if payload.get("share_with_third_party") and not payload.get("has_active_baa"):
        return False, "HIPAA_BAA_REQUIRED: Sharing Protected Health Information with external partners requires a signed Business Associate Agreement (BAA)"

    # 3. Clinical Safety: EHR Provenance for Tier 3+ medical actions
    if intent.risk_tier >= 3 and not payload.get("provenance_id"):
        return False, "MISSING_CLINICAL_PROVENANCE: Tier 3+ clinical actions must log a valid source EHR provenance_id"

    # 4. Medication Order Gate: Break-Glass authorization for controlled substance orders
    if intent.action_type == "MEDICATION_ORDER" and payload.get("is_controlled_substance"):
        if not payload.get("break_glass_authorized"):
            return False, "BREAK_GLASS_REQUIRED: Controlled substance orders require explicit break-glass authorization"

    return True, ""

