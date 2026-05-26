import { Kernel } from "../kernel.js";
import { cybersecurityPolicy } from "../policies/cybersecurity.js";
import { financePolicy } from "../policies/finance.js";
import { healthcarePolicy } from "../policies/healthcare.js";
import { v4 as uuidv4 } from "uuid";

const kernel = new Kernel();
kernel.registerPolicy(cybersecurityPolicy);
kernel.registerPolicy(financePolicy);
kernel.registerPolicy(healthcarePolicy);

async function healthCareDemo() {
  console.log("=== DASC Node Healthcare Safety Demo ===\n");

  // 1. PHI Leak Prevention
  console.log("--- Testing PHI Leak Prevention ---");
  const leakIntent = {
    intent_id: uuidv4(),
    actor_agent: "clinical-assistant",
    action_type: "LOG_ENCOUNTER",
    risk_tier: 1,
    evidence: [{ source_type: "trusted" }],
    payload: { note: "Patient John Doe with SSN 123-45-6789 reported fever." }
  };
  const dec1 = kernel.evaluate(leakIntent as any);
  console.log(`Status: ${dec1.status} | Reason: ${dec1.reason_codes[0]}`);

  // 2. Clinical Provenance Verification
  console.log("\n--- Testing Clinical Provenance (Tier 3) ---");
  const medicalIntent = {
    intent_id: uuidv4(),
    actor_agent: "diagnosis-agent",
    action_type: "ORDER_LABS",
    risk_tier: 3,
    evidence: [{ source_type: "trusted" }],
    payload: { test: "CBC", patient_id: "P-101" } // Missing provenance_id
  };
  const dec2 = kernel.evaluate(medicalIntent as any);
  console.log(`Status: ${dec2.status} | Reason: ${dec2.reason_codes[0]}`);

  // 3. Valid Clinical Action
  console.log("\n--- Testing Valid Authorized Medical Action ---");
  const validIntent = {
    intent_id: uuidv4(),
    actor_agent: "doctor-agent",
    action_type: "MEDICATION_ORDER",
    risk_tier: 2,
    evidence: [{ source_type: "trusted" }],
    payload: { medication: "Amoxicillin", provenance_id: "EHR-99221" }
  };
  const dec3 = kernel.evaluate(validIntent as any);
  console.log(`Status: ${dec3.status}`);
}

healthCareDemo().catch(console.error);
