import { Intent } from "../types.js";

/**
 * Healthcare Policy Adapter
 * Focuses on HIPAA compliance, PHI protection, and clinical provenance.
 */
export const healthcarePolicy = (intent: Intent): { pass: boolean; reason?: string } => {
  const payloadString = JSON.stringify(intent.payload);

  // 1. Detect unmasked PHI (Simple regex for SSN/Email as a proxy for PHI)
  const phiPatterns = [
    /\b\d{3}-\d{2}-\d{4}\b/, // SSN
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/ // Email
  ];

  for (const pattern of phiPatterns) {
    if (pattern.test(payloadString)) {
      return { pass: false, reason: "PHI_DETECTED: Intent contains unmasked patient identifiable information" };
    }
  }

  // 2. Enforce Clinical Provenance for sensitive actions
  if (intent.risk_tier >= 3 && !intent.payload.provenance_id) {
    return { 
        pass: false, 
        reason: "MISSING_CLINICAL_PROVENANCE: Tier 3+ medical actions must reference a source EHR provenance_id" 
    };
  }

  // 3. Break-Glass enforcement for high-risk medication
  if (intent.action_type === "MEDICATION_ORDER" && intent.payload.is_controlled_substance) {
    if (!intent.payload.break_glass_authorized) {
        return { pass: false, reason: "BREAK_GLASS_REQUIRED: Controlled substance orders require explicit authorization" };
    }
  }

  return { pass: true };
};
