import { describe, it, expect, beforeEach } from "vitest";
import { Kernel } from "../src/kernel.js";
import { DASCLangGraphAdapter, DASCLangGraphCheckpointer } from "../src/adapters/langgraph.js";
import { DASCCrewAIAdapter } from "../src/adapters/crewai.js";
import { DASCSemanticKernelAdapter } from "../src/adapters/semantic_kernel.js";

describe("DASC Framework Adapters", () => {
  let kernel: Kernel;

  beforeEach(() => {
    kernel = new Kernel({}, ":memory:");
  });

  it("should intercept unsafe intents in LangGraph SafetyNode", async () => {
    const adapter = new DASCLangGraphAdapter(kernel);
    const unsafeState = {
      proposed_intent: {
        intent_id: "lg-1",
        actor_agent: "graph-agent",
        action_type: "DELETE_ALL",
        risk_tier: 4, // Mandatory escalation
        evidence: [{ source_type: "trusted" }]
      }
    };

    const result = await adapter.safetyNode(unsafeState);
    expect(result.last_decision?.status).toBe("ESCALATE");
  });

  it("should wrap and block unsafe CrewAI tasks", async () => {
    const adapter = new DASCCrewAIAdapter(kernel);
    const guard = adapter.createGuardrail("crew-agent", 2);

    // Mock a rejection policy
    kernel.registerPolicy(() => ({ pass: false, reason: "MOCK_REJECT" }));

    const taskOutput = { action: "delete_database" };

    await expect(guard(taskOutput)).rejects.toThrow("DASC_SAFETY_VIOLATION");
  });

  it("should filter unsafe Semantic Kernel functions", async () => {
    const adapter = new DASCSemanticKernelAdapter(kernel);
    const filter = adapter.createFunctionFilter();
    
    const context = {
      function: { name: "dangerous_func", metadata: { risk_tier: 4 } },
      arguments: {}
    };

    const next = async () => {};

    await expect(filter(context, next)).rejects.toThrow("DASC_ESCALATE");
  });

  it("should save and load checkpoints using DASCLangGraphCheckpointer", async () => {
    const checkpointer = new DASCLangGraphCheckpointer(":memory:");
    const config = { configurable: { thread_id: "thread-xyz" } };
    const checkpoint: any = {
      id: "chk-xyz",
      ts: "2026-05-26T10:00:00Z",
      v: 1,
      channel_values: { val: 42 }
    };
    const metadata = { source: "test-js" };

    // 1. Put
    const res = await checkpointer.put(config, checkpoint, metadata);
    expect(res.configurable.checkpoint_id).toBe("chk-xyz");

    // 2. Get
    const tup = await checkpointer.getTuple(config);
    expect(tup).toBeDefined();
    expect(tup?.checkpoint.id).toBe("chk-xyz");
    expect((tup?.checkpoint as any).channel_values.val).toBe(42);
    expect(tup?.metadata.source).toBe("test-js");
  });
});
