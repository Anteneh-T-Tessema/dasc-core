import re
import json
from ..schemas import Intent

def healthcare_policy(intent: Intent):
    """
    Healthcare Policy
    Focuses on HIPAA compliance, PHI protection, and clinical provenance.
    """
    payload = getattr(intent, "payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}

    payload_str = json.dumps(payload)

    # 1. Detect unmasked PHI (Simple regex for SSN/Email as a proxy for PHI)
    phi_patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"  # Email
    ]

    for pattern in phi_patterns:
        if re.search(pattern, payload_str):
            return False, "PHI_DETECTED: Intent contains unmasked patient identifiable information"

    # 2. Enforce Clinical Provenance for sensitive actions
    if intent.risk_tier >= 3 and not payload.get("provenance_id"):
        return False, "MISSING_CLINICAL_PROVENANCE: Tier 3+ medical actions must reference a source EHR provenance_id"

    # 3. Break-Glass enforcement for high-risk medication
    if intent.action_type == "MEDICATION_ORDER" and payload.get("is_controlled_substance"):
        if not payload.get("break_glass_authorized"):
            return False, "BREAK_GLASS_REQUIRED: Controlled substance orders require explicit authorization"

    return True, ""
