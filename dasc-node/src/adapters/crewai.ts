import { Kernel } from "../kernel.js";
import { Intent } from "../types.js";
import { v4 as uuidv4 } from "uuid";

/**
 * CrewAI-JS Adapter (Conceptual)
 * 
 * Provides a 'Guardrail' task wrapper for CrewAI agents.
 */

export class DASCCrewAIAdapter {
  private kernel: Kernel;

  constructor(kernel: Kernel) {
    this.kernel = kernel;
  }

  /**
   * Wraps a CrewAI Task execution with a DASC safety check.
   */
  public createGuardrail(agentName: string, riskTier: number = 1) {
    return async (taskOutput: any) => {
      const intent: Intent = {
        intent_id: uuidv4(),
        actor_agent: agentName,
        action_type: "CREW_TASK_COMMIT",
        risk_tier: riskTier,
        evidence: [{ source_type: "trusted" }],
        payload: taskOutput
      };

      const decision = this.kernel.evaluate(intent);

      if (decision.status !== "COMMIT") {
        throw new Error(`DASC_SAFETY_VIOLATION: Task rejected. Reason: ${decision.reason_codes.join(", ")}`);
      }

      return taskOutput;
    };
  }
}
