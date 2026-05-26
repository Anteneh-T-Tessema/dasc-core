import { Kernel } from "./kernel.js";
import { Intent } from "./types.js";
import { v4 as uuidv4 } from "uuid";

/**
 * DASC Gate Wrapper
 * Higher-order function that protects any asynchronous function with a DASC safety check.
 */
export function dascGate(kernel: Kernel, options: { riskTier: number, actor: string }) {
  return function <T extends (...args: any[]) => Promise<any>>(fn: T) {
    return async function (...args: Parameters<T>): Promise<ReturnType<T>> {
      const intent: Intent = {
        intent_id: uuidv4(),
        actor_agent: options.actor,
        action_type: fn.name || "UNNAMED_FUNCTION",
        risk_tier: options.riskTier,
        evidence: [{ source_type: "trusted" }],
        payload: { args },
      };

      const decision = kernel.evaluate(intent);

      if (decision.status === "REJECT") {
        throw new Error(`DASC_REJECT: ${decision.reason_codes.join(", ")}`);
      }

      if (decision.status === "ESCALATE") {
        throw new Error(`DASC_ESCALATE: Manual approval required for ${intent.intent_id}`);
      }

      return await fn(...args);
    };
  };
}
