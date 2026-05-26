import { describe, it, expect, beforeEach } from "vitest";
import { Kernel } from "../src/kernel.js";
import { Intent } from "../src/types.js";
import { cybersecurityPolicy } from "../src/policies/cybersecurity.js";
import { DeclarativePolicyEngine } from "../src/policies/declarative.js";
import { healthcarePolicy } from "../src/policies/healthcare.js";
import { privacyPolicy } from "../src/policies/privacy.js";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

describe("DASC Node Kernel Enterprise Hardening", () => {
  let kernel: Kernel;

  beforeEach(() => {
    // Reset kernel and state for each test
    kernel = new Kernel({ "config.json": "v1.0.0" }, ":memory:");
    kernel.registerPolicy(cybersecurityPolicy);
  });

  it("should COMMIT a safe intent and create a valid hash chain", () => {
    const intent: Intent = {
      intent_id: "integrity-1",
      actor_agent: "security-bot",
      action_type: "READ",
      risk_tier: 1,
      evidence: [{ source_type: "trusted" }],
      payload: { path: "data.txt" }
    };
    kernel.evaluate(intent);
    
    // Verify the ledger is intact
    const isIntact = (kernel as any).ledger.verifyIntegrity();
    expect(isIntact).toBe(true);
  });

  it("should scrub PII from the ledger (Sanitization)", () => {
    const intent: Intent = {
      intent_id: "privacy-1",
      actor_agent: "log-agent",
      action_type: "LOG",
      risk_tier: 1,
      evidence: [{ source_type: "trusted" }],
      payload: { 
          note: "Leaking PII: user@example.com and SSN 123-45-6789" 
      }
    };
    kernel.evaluate(intent);
    
    const history = (kernel as any).ledger.getHistory(1);
    const intentJson = history[0].intent_json;
    
    expect(intentJson).not.toContain("user@example.com");
    expect(intentJson).not.toContain("123-45-6789");
    expect(intentJson).toContain("[REDACTED_EMAIL]");
    expect(intentJson).toContain("[REDACTED_SSN]");
  });

  it("should detect hash chain tampering", () => {
    const intent: Intent = {
      intent_id: "tamper-1",
      actor_agent: "honest-agent",
      action_type: "WRITE",
      risk_tier: 1,
      evidence: [{ source_type: "trusted" }],
      payload: { data: "original" }
    };
    kernel.evaluate(intent);

    // Manually tamper with the database record
    const db = (kernel as any).ledger.db;
    db.prepare("UPDATE ledger SET status = 'REJECT' WHERE intent_id = 'tamper-1'").run();

    // Verify integrity should now fail
    const isIntact = (kernel as any).ledger.verifyIntegrity();
    expect(isIntact).toBe(false);
  });

  it("should evaluate dynamic rules using DeclarativePolicyEngine", () => {
    const rules = {
      rules: [
        {
          name: "limit_spending",
          condition: "payload.amount > 1000 and risk_tier < 3",
          action: "REJECT" as const,
          reason: "OVER_SPENT"
        },
        {
          name: "nuke_prevention",
          condition: "action_type == 'NUKE'",
          action: "ESCALATE" as const,
          reason: "NUKE_GATE"
        }
      ]
    };

    const engine = new DeclarativePolicyEngine(rules);
    
    const localKernel = new Kernel({}, ":memory:");
    localKernel.registerPolicy(engine.evaluatePolicies);

    // 1. Matches rule 1
    const intent1: Intent = {
      intent_id: "D1",
      actor_agent: "agent",
      action_type: "transfer",
      risk_tier: 1,
      evidence: [],
      payload: { amount: 1500 }
    };
    const dec1 = localKernel.evaluate(intent1);
    expect(dec1.status).toBe("REJECT");
    expect(dec1.reason_codes).toContain("CUSTOM_POLICY_VIOLATION: OVER_SPENT");

    // 2. Matches rule 2 (escalate)
    const intent2: Intent = {
      intent_id: "D2",
      actor_agent: "agent",
      action_type: "NUKE",
      risk_tier: 1,
      evidence: [],
      payload: {}
    };
    const dec2 = localKernel.evaluate(intent2);
    expect(dec2.status).toBe("ESCALATE");
    expect(dec2.reason_codes[0]).toContain("NUKE_GATE");
  });

  it("should enforce HIPAA, BAA, MRN and clinical provenance in healthcarePolicy", () => {
    kernel.registerPolicy(healthcarePolicy);

    // 1. HIPAA violation (unmasked MRN)
    const intent1: Intent = {
      intent_id: "H1",
      actor_agent: "agent",
      action_type: "fetch",
      risk_tier: 1,
      evidence: [],
      payload: { mrn_id: "MRN-1234-5678" }
    };
    const dec1 = kernel.evaluate(intent1);
    expect(dec1.status).toBe("REJECT");
    expect(dec1.reason_codes[0]).toContain("PHI_DETECTED");

    // 2. BAA violation (third party sharing without BAA)
    const intent2: Intent = {
      intent_id: "H2",
      actor_agent: "agent",
      action_type: "fetch",
      risk_tier: 1,
      evidence: [],
      payload: { share_with_third_party: true, has_active_baa: false }
    };
    const dec2 = kernel.evaluate(intent2);
    expect(dec2.status).toBe("REJECT");
    expect(dec2.reason_codes[0]).toContain("HIPAA_BAA_REQUIRED");

    // 3. Clinical provenance missing (Tier 3 action)
    const intent3: Intent = {
      intent_id: "H3",
      actor_agent: "agent",
      action_type: "prescribe",
      risk_tier: 3,
      evidence: [],
      payload: { provenance_id: "" },
      compensation_plan: { undo: "revert" }
    };
    const dec3 = kernel.evaluate(intent3);
    expect(dec3.status).toBe("REJECT");
    expect(dec3.reason_codes[0]).toContain("MISSING_CLINICAL_PROVENANCE");
  });

  it("should enforce GDPR consent, sovereignty, minor checks, and purge rules in privacyPolicy", () => {
    kernel.registerPolicy(privacyPolicy);

    // 1. Consent missing for EU residency
    const intent1: Intent = {
      intent_id: "P1",
      actor_agent: "agent",
      action_type: "process",
      risk_tier: 1,
      evidence: [],
      payload: { user_residency: "EU", contains_personal_data: true, consent_obtained: false }
    };
    const dec1 = kernel.evaluate(intent1);
    expect(dec1.status).toBe("REJECT");
    expect(dec1.reason_codes[0]).toContain("GDPR_CONSENT_REQUIRED");

    // 2. Data sovereignty (EU residency to US region without SCC)
    const intent2: Intent = {
      intent_id: "P2",
      actor_agent: "agent",
      action_type: "process",
      risk_tier: 1,
      evidence: [],
      payload: { user_residency: "EU", target_region: "US", has_scc: false }
    };
    const dec2 = kernel.evaluate(intent2);
    expect(dec2.status).toBe("REJECT");
    expect(dec2.reason_codes[0]).toContain("GDPR_SOVEREIGNTY_VIOLATION");

    // 3. Child protection (minor under 16 without parental consent)
    const intent3: Intent = {
      intent_id: "P3",
      actor_agent: "agent",
      action_type: "process",
      risk_tier: 1,
      evidence: [],
      payload: { user_age: 14, parental_consent_verified: false }
    };
    const dec3 = kernel.evaluate(intent3);
    expect(dec3.status).toBe("REJECT");
    expect(dec3.reason_codes[0]).toContain("GDPR_CHILD_PROTECTION");

    // 4. Purging restrictions (non-compliance agent purging data)
    const intent4: Intent = {
      intent_id: "P4",
      actor_agent: "junior-bot",
      action_type: "PURGE_USER_DATA",
      risk_tier: 2,
      evidence: [],
      payload: {}
    };
    const dec4 = kernel.evaluate(intent4);
    expect(dec4.status).toBe("REJECT");
    expect(dec4.reason_codes[0]).toContain("PRIVILEGE_MISMATCH");
  });

  it("should load declarative rules from a directory (rules merging)", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "dasc-rules-"));

    const rule1 = {
      rules: [
        {
          name: "Rule A",
          condition: "payload.val > 10",
          action: "REJECT" as const,
          reason: "VAL_TOO_HIGH"
        }
      ]
    };

    const rule2 = {
      rules: [
        {
          name: "Rule B",
          condition: "action_type == 'TEST'",
          action: "REJECT" as const,
          reason: "NO_TEST_ALLOWED"
        }
      ]
    };

    fs.writeFileSync(path.join(tmpDir, "rule1.json"), JSON.stringify(rule1));
    fs.writeFileSync(path.join(tmpDir, "rule2.json"), JSON.stringify(rule2));

    const engine = new DeclarativePolicyEngine();
    engine.loadRulesFromDirectory(tmpDir);

    const localKernel = new Kernel({}, ":memory:");
    localKernel.registerPolicy(engine.evaluatePolicies);

    const intent1: Intent = {
      intent_id: "T1",
      actor_agent: "agent",
      action_type: "run",
      risk_tier: 1,
      evidence: [],
      payload: { val: 15 }
    };
    const dec1 = localKernel.evaluate(intent1);
    expect(dec1.status).toBe("REJECT");
    expect(dec1.reason_codes[0]).toContain("VAL_TOO_HIGH");

    const intent2: Intent = {
      intent_id: "T2",
      actor_agent: "agent",
      action_type: "TEST",
      risk_tier: 1,
      evidence: [],
      payload: { val: 5 }
    };
    const dec2 = localKernel.evaluate(intent2);
    expect(dec2.status).toBe("REJECT");
    expect(dec2.reason_codes[0]).toContain("NO_TEST_ALLOWED");

    // cleanup
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("should dynamically import imperative TS/JS policies from a directory", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "dasc-policies-"));
    
    const policyCode = `
export const customTestPolicy = (intent) => {
  const payload = intent.payload || {};
  if (payload.blocked) {
    return { pass: false, reason: "DYNAMIC_JS_BLOCKED" };
  }
  return { pass: true };
};
`;
    const tempFilePath = path.join(tempDir, "customPolicy.js");
    fs.writeFileSync(tempFilePath, policyCode, "utf-8");

    const localKernel = new Kernel({}, ":memory:");

    // Emulate server.ts loading logic
    const files = fs.readdirSync(tempDir);
    for (const file of files) {
      if (file.endsWith(".js") || file.endsWith(".ts")) {
        const filePath = path.resolve(tempDir, file);
        const moduleUrl = `file://${filePath}`;
        const module = await import(moduleUrl);
        for (const [key, value] of Object.entries(module)) {
          if (typeof value === "function" && key.endsWith("Policy")) {
            localKernel.registerPolicy(value as any);
          }
        }
      }
    }

    const intent1: Intent = {
      intent_id: "TI1",
      actor_agent: "agent",
      action_type: "run",
      risk_tier: 1,
      evidence: [],
      payload: { blocked: true }
    };
    const dec1 = localKernel.evaluate(intent1);
    expect(dec1.status).toBe("REJECT");
    expect(dec1.reason_codes[0]).toContain("DYNAMIC_JS_BLOCKED");

    const intent2: Intent = {
      intent_id: "TI2",
      actor_agent: "agent",
      action_type: "run",
      risk_tier: 1,
      evidence: [],
      payload: { blocked: false }
    };
    const dec2 = localKernel.evaluate(intent2);
    expect(dec2.status).toBe("COMMIT");

    // cleanup
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  it("should evaluate dynamic rules for new verticals (Security, Legal, CRM, Supply Chain)", () => {
    const rules = {
      rules: [
        {
          name: "Database Exfiltration Guard",
          condition: "target_artifact in ['database', 'backup'] and action_type == 'READ' and actor_agent != 'security-agent'",
          action: "ESCALATE" as const,
          reason: "SECURITY_EXFILTRATION_OVERWATCH"
        },
        {
          name: "CCPA Data Deletion Gate",
          condition: "action_type == 'DELETE_CUSTOMER_DATA' and payload.ccpa_verified == false",
          action: "REJECT" as const,
          reason: "CCPA_COMPLIANCE"
        },
        {
          name: "CRM Bulk Export Guard",
          condition: "action_type == 'EXPORT_CRM_CONTACTS' and payload.record_count > 100",
          action: "ESCALATE" as const,
          reason: "CRM_DATA_LEAK_PREVENTION"
        },
        {
          name: "Supply Chain Order Limit",
          condition: "action_type == 'PLACE_PURCHASE_ORDER' and payload.total_cost > 50000",
          action: "ESCALATE" as const,
          reason: "SUPPLY_CHAIN_LIMIT"
        }
      ]
    };

    const engine = new DeclarativePolicyEngine(rules);
    const localKernel = new Kernel({}, ":memory:");
    localKernel.registerPolicy(engine.evaluatePolicies);

    // 1. Security Check
    const intentSecPass: Intent = {
      intent_id: "S1", actor_agent: "standard-agent", action_type: "READ", target_artifact: "file.txt", risk_tier: 1, evidence: []
    };
    expect(localKernel.evaluate(intentSecPass).status).toBe("COMMIT");

    const intentSecFail: Intent = {
      intent_id: "S2", actor_agent: "standard-agent", action_type: "READ", target_artifact: "database", risk_tier: 1, evidence: []
    };
    expect(localKernel.evaluate(intentSecFail).status).toBe("ESCALATE");

    // 2. CCPA Check
    const intentCcpaFail: Intent = {
      intent_id: "L1", actor_agent: "compliance-agent", action_type: "DELETE_CUSTOMER_DATA", target_artifact: "crm", risk_tier: 2, evidence: [],
      payload: { ccpa_verified: false }
    };
    expect(localKernel.evaluate(intentCcpaFail).status).toBe("REJECT");

    // 3. CRM Check
    const intentCrmFail: Intent = {
      intent_id: "C1", actor_agent: "crm-bot", action_type: "EXPORT_CRM_CONTACTS", target_artifact: "contacts", risk_tier: 2, evidence: [],
      payload: { record_count: 150 }
    };
    expect(localKernel.evaluate(intentCrmFail).status).toBe("ESCALATE");

    // 4. Supply Chain Check
    const intentScFail: Intent = {
      intent_id: "SC1", actor_agent: "procurement-bot", action_type: "PLACE_PURCHASE_ORDER", target_artifact: "vendor_db", risk_tier: 2, evidence: [],
      payload: { total_cost: 60000 }
    };
    expect(localKernel.evaluate(intentScFail).status).toBe("ESCALATE");
  });
});
