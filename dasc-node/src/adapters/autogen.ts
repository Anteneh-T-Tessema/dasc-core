import { Kernel } from "../kernel.js";
import { Intent } from "../types.js";
import { v4 as uuidv4 } from "uuid";

/**
 * AutoGen-JS Adapter
 * 
 * Provides a 'SafetyReviewer' agent pattern for AutoGen conversations.
 */

export class DASCAutoGenAdapter {
  private kernel: Kernel;

  constructor(kernel: Kernel) {
    this.kernel = kernel;
  }

  /**
   * Generates a safety review for an agent's proposed action.
   * This can be used as a 'tool' or a 'function' that agents MUST call before execution.
   */
  public safetyReviewTool = async (proposal: any) => {
    const intent: Intent = {
      intent_id: uuidv4(),
      actor_agent: proposal.agent_name || "autogen-agent",
      action_type: proposal.action_type || "TASK_EXECUTION",
      risk_tier: proposal.risk_tier || 1,
      evidence: [{ source_type: "trusted" }],
      payload: proposal.payload || {}
    };

    const decision = this.kernel.evaluate(intent);

    if (decision.status === "COMMIT") {
      return { 
          authorized: true, 
          decision_id: decision.intent_id, 
          message: "DASC_AUTHORIZED: Action is safe to proceed." 
      };
    } else {
      return { 
          authorized: false, 
          decision_id: decision.intent_id, 
          message: `DASC_REJECTED: ${decision.reason_codes.join(", ")}`,
          suggestions: decision.suggestions
      };
    }
  };
}
