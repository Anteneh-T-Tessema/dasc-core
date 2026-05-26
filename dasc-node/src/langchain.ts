import { Tool } from "@langchain/core/tools";
import { Kernel } from "./kernel.js";
import { Intent } from "./types.js";
import { v4 as uuidv4 } from "uuid";

export class DASCCommitTool extends Tool {
  name = "dasc_commit";
  description = "A safety gatekeeper tool. Use this to commit ANY action that has side effects (file writes, DB changes, API calls). Input should be a JSON object with 'action_type', 'risk_tier', and 'payload'.";
  
  private kernel: Kernel;

  constructor(kernel: Kernel) {
    super();
    this.kernel = kernel;
  }

  async _call(input: string): Promise<string> {
    try {
      const params = JSON.parse(input);
      const intent: Intent = {
        intent_id: uuidv4(),
        actor_agent: "langchain-agent",
        action_type: params.action_type || "UNKNOWN",
        risk_tier: params.risk_tier || 1,
        evidence: [{ source_type: "trusted" }],
        payload: params.payload || {},
        state_version_vector: params.state_version_vector,
        compensation_plan: params.compensation_plan
      };

      const decision = this.kernel.evaluate(intent);

      if (decision.status === "COMMIT") {
        return `DASC_COMMIT_SUCCESS: Action authorized. Decision ID: ${decision.intent_id}`;
      } else if (decision.status === "ESCALATE") {
        return `DASC_ESCALATE: This action requires human approval. Monitor the DASC Dashboard for Intent ID: ${decision.intent_id}`;
      } else {
        return `DASC_REJECT: Action denied. Reasons: ${decision.reason_codes.join(", ")}. Suggestions: ${decision.suggestions.join(" ")}`;
      }
    } catch (err: any) {
      return `DASC_ERROR: Failed to parse intent. ${err.message}`;
    }
  }
}
