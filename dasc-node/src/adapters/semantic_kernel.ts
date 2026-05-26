import { Kernel } from "../kernel.js";
import { Intent } from "../types.js";
import { v4 as uuidv4 } from "uuid";

/**
 * Microsoft Semantic Kernel (JS) Adapter
 * 
 * Provides a Pre-Invocation Filter for SK Functions.
 */

export class DASCSemanticKernelAdapter {
  private kernel: Kernel;

  constructor(kernel: Kernel) {
    this.kernel = kernel;
  }

  /**
   * Semantic Kernel Function Filter
   * Intercepts function execution to evaluate intent.
   */
  public createFunctionFilter() {
    return async (context: any, next: () => Promise<void>) => {
      const intent: Intent = {
        intent_id: uuidv4(),
        actor_agent: "semantic-kernel-agent",
        action_type: context.function.name,
        risk_tier: context.function.metadata?.risk_tier || 1,
        evidence: [{ source_type: "trusted" }],
        payload: context.arguments || {}
      };

      const decision = this.kernel.evaluate(intent);

      if (decision.status === "REJECT") {
        throw new Error(`DASC_SAFETY_VIOLATION: ${decision.reason_codes.join(", ")}`);
      }

      if (decision.status === "ESCALATE") {
        throw new Error(`DASC_ESCALATE: Manual approval required via DASC Dashboard. ID: ${intent.intent_id}`);
      }

      await next();
    };
  }
}
