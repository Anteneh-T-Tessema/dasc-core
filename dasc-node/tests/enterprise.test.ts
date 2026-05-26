import { describe, it, expect, beforeEach } from "vitest";
import { Kernel } from "../src/kernel.js";
import { Intent } from "../src/types.js";
import { cybersecurityPolicy } from "../src/policies/cybersecurity.js";
import { DeclarativePolicyEngine } from "../src/policies/declarative.js";

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
});
