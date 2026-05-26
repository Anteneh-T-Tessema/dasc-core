import { Intent } from "../types.js";

/**
 * Healthcare Policy Adapter
 * Focuses on HIPAA compliance, PHI/PII protection, clinical EHR provenance, and BAA requirements.
 */
export const healthcarePolicy = (intent: Intent): { pass: boolean; reason?: string } => {
  const payload = intent.payload || {};
  const payloadString = JSON.stringify(payload);

  // 1. HIPAA Privacy: Scan for unmasked PHI (SSN, Email, MRN, Phone)
  const phiPatterns = {
    SSN: /\b\d{3}-\d{2}-\d{4}\b/,
    Email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
    MRN: /\bMRN-\d{4}-\d{4}\b/, // Medical Record Number
    Phone: /\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/
  };

  for (const [name, pattern] of Object.entries(phiPatterns)) {
    if (pattern.test(payloadString)) {
      if (!payload.is_encrypted && !payload.is_tokenized) {
        return { pass: false, reason: `PHI_DETECTED: Intent contains unmasked patient identifiable information (${name})` };
      }
    }
  }

  // 2. HIPAA Administrative: Enforce BAA (Business Associate Agreement) for external sharing
  if (payload.share_with_third_party && !payload.has_active_baa) {
    return {
      pass: false,
      reason: "HIPAA_BAA_REQUIRED: Sharing Protected Health Information with external partners requires a signed Business Associate Agreement (BAA)"
    };
  }

  // 3. Clinical Safety: EHR Provenance for Tier 3+ medical actions
  if (intent.risk_tier >= 3 && !payload.provenance_id) {
    return { 
      pass: false, 
      reason: "MISSING_CLINICAL_PROVENANCE: Tier 3+ clinical actions must log a valid source EHR provenance_id" 
    };
  }

  // 4. Medication Order Gate: Break-Glass authorization for controlled substance orders
  if (intent.action_type === "MEDICATION_ORDER" && payload.is_controlled_substance) {
    if (!payload.break_glass_authorized) {
      return { pass: false, reason: "BREAK_GLASS_REQUIRED: Controlled substance orders require explicit break-glass authorization" };
    }
  }

  return { pass: true };
};
