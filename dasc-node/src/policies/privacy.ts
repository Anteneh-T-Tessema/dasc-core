import { Intent } from "../types.js";

/**
 * Privacy Policy Adapter (GDPR / Data Minimization / Sovereignty)
 * Focuses on GDPR consent requirements, sovereignty borders, parental consent, and right to be forgotten (purge actions).
 */
export const privacyPolicy = (intent: Intent): { pass: boolean; reason?: string } => {
  const payload = intent.payload || {};

  // 1. GDPR Consent Check: If processing personal data for an EU resident, consent is mandatory
  if (payload.user_residency === "EU" && payload.contains_personal_data) {
    if (!payload.consent_obtained) {
      return {
        pass: false,
        reason: "GDPR_CONSENT_REQUIRED: Processing personal data of EU residents requires explicit user consent"
      };
    }
  }

  // 2. GDPR Data Sovereignty: EU user records must not leave the EU region unless standard contractual clauses (SCC) are present
  if (payload.user_residency === "EU" && payload.target_region && payload.target_region !== "EU") {
    if (!payload.has_scc) {
      return {
        pass: false,
        reason: "GDPR_SOVEREIGNTY_VIOLATION: Transborder flow of EU personal data outside EU requires Standard Contractual Clauses (SCC)"
      };
    }
  }

  // 3. Child Protection (GDPR / COPPA): Users under 16 require parent consent for data handling
  if (payload.user_age && typeof payload.user_age === "number" && payload.user_age < 16) {
    if (!payload.parental_consent_verified) {
      return {
        pass: false,
        reason: "GDPR_CHILD_PROTECTION: Handling data of minors under 16 requires verified parental consent"
      };
    }
  }

  // 4. Right to be Forgotten (Purging): Only authorized agents can perform hard purges of user records
  if (intent.action_type === "PURGE_USER_DATA") {
    const actor = (intent.actor_agent || "").toLowerCase();
    if (!actor.includes("compliance") && !actor.includes("admin")) {
      return {
        pass: false,
        reason: "PRIVILEGE_MISMATCH: Only compliance or admin agents are authorized to purge user databases"
      };
    }
  }

  return { pass: true };
};
