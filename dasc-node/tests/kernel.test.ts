import { describe, it, expect, beforeEach } from "vitest";
import { Kernel } from "../src/kernel.js";
import { Intent } from "../src/types.js";
import { cybersecurityPolicy } from "../src/policies/cybersecurity.js";

describe("DASC Node Kernel", () => {
  let kernel: Kernel;

  beforeEach(() => {
    kernel = new Kernel({ "config.json": "v1.0.0" }, ":memory:");
    kernel.registerPolicy(cybersecurityPolicy);
  });

  it("should COMMIT a safe intent", () => {
    const intent: Intent = {
      intent_id: "test-1",
      actor_agent: "agent-007",
      action_type: "READ",
      risk_tier: 1,
      evidence: [{ source_type: "trusted" }],
      payload: { path: "hello.txt" }
    };
    const decision = kernel.evaluate(intent);
    expect(decision.status).toBe("COMMIT");
  });

  it("should REJECT a dangerous command (Cybersecurity Policy)", () => {
    const intent: Intent = {
      intent_id: "test-2",
      actor_agent: "agent-007",
      action_type: "EXEC",
      risk_tier: 2,
      evidence: [{ source_type: "trusted" }],
      payload: { command: "rm -rf /" }
    };
    const decision = kernel.evaluate(intent);
    expect(decision.status).toBe("REJECT");
    expect(decision.reason_codes).toContain("CUSTOM_POLICY_VIOLATION: DANGEROUS_COMMAND_DETECTED: rm -rf");
  });

  it("should REJECT a stale state (OCC Violation)", () => {
    const intent: Intent = {
      intent_id: "test-3",
      actor_agent: "agent-007",
      action_type: "WRITE",
      risk_tier: 1,
      state_version_vector: { "config.json": "v0.9.0" },
      evidence: [{ source_type: "trusted" }],
      payload: { content: "update" }
    };
    const decision = kernel.evaluate(intent);
    expect(decision.status).toBe("REJECT");
    expect(decision.reason_codes[0]).toContain("OCC_CONFLICT");
  });

  it("should ESCALATE a Tier 4 action", () => {
    const intent: Intent = {
      intent_id: "test-4",
      actor_agent: "admin-agent",
      action_type: "NUKE",
      risk_tier: 4,
      evidence: [{ source_type: "trusted" }],
      payload: {}
    };
    const decision = kernel.evaluate(intent);
    expect(decision.status).toBe("ESCALATE");
  });
});
