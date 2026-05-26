import { Intent, Decision, DASCStatus } from "./types.js";
import { BitemporalLedger } from "./ledger.js";
import { NotificationManager } from "./notifications.js";

export type PolicyFunc = (intent: Intent) => { pass: boolean; reason?: string };

export class Kernel {
  private ledger: BitemporalLedger;
  private notifier: NotificationManager;
  private current_state_versions: Record<string, string>;
  private policies: PolicyFunc[] = [];

  constructor(current_state_versions: Record<string, string> = {}, dbPath?: string) {
    this.ledger = new BitemporalLedger(dbPath);
    this.notifier = new NotificationManager();
    this.current_state_versions = current_state_versions;
  }

  registerPolicy(policy: PolicyFunc) {
    this.policies.push(policy);
  }

  async approveIntent(intent_id: string, approved: boolean, approver: string): Promise<Decision> {
    const history = this.ledger.getHistory();
    const target = (history as any[]).find((h: any) => h.intent_id === intent_id);

    if (!target) throw new Error("Intent not found");
    if (target.status !== "ESCALATE") throw new Error("Only escalated intents can be approved");

    const status: DASCStatus = approved ? "COMMIT" : "REJECT";
    const decision: Decision = {
      intent_id,
      status,
      reason_codes: [`MANUAL_${status}_BY_${approver}`],
      suggestions: [],
      timestamp: new Date().toISOString()
    };

    this.ledger.logDecision(JSON.parse(target.intent_json), decision);
    return decision;
  }

  evaluate(intent: Intent): Decision {
    const reasons: string[] = [];
    
    // 1. IFC / Taint Check
    for (const ev of intent.evidence) {
      if (ev.source_type === "untrusted" && intent.risk_tier >= 2) {
        reasons.push(`IFC_TAINT_DETECTED: Untrusted evidence for Tier ${intent.risk_tier}`);
      }
    }

    // 2. OCC / Version Check
    if (intent.state_version_vector) {
      for (const [artifact, version] of Object.entries(intent.state_version_vector)) {
        const current_v = this.current_state_versions[artifact];
        if (current_v && current_v !== version) {
          reasons.push(`OCC_CONFLICT: ${artifact} changed from ${version} to ${current_v}`);
        }
      }
    }

    // 3. Risk Tier Policy
    if (intent.risk_tier >= 3 && !intent.compensation_plan) {
      reasons.push("MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK");
    }

    // 4. Custom Policies
    for (const policy of this.policies) {
      const result = policy(intent);
      if (!result.pass) {
        reasons.push(`CUSTOM_POLICY_VIOLATION: ${result.reason}`);
      }
    }

    // 5. Formulate Decision
    let status: DASCStatus = "COMMIT";
    if (reasons.length > 0) {
      status = reasons.some(r => r.includes("TIER_4") || r.includes("HIGH_RISK")) ? "ESCALATE" : "REJECT";
    } else if (intent.risk_tier === 4) {
      status = "ESCALATE";
      reasons.push("TIER_4_MANDATORY_ESCALATION");
    }

    const suggestions: string[] = [];
    if (status !== "COMMIT") {
      if (reasons.includes("MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK")) {
        suggestions.push("Provide a 'compensation_plan' (e.g. {undo: 'revert'})");
      }
      if (status === "ESCALATE") {
        suggestions.push("Human approval required via Control Plane.");
      }
    }

    const decision: Decision = {
      intent_id: intent.intent_id,
      status,
      reason_codes: reasons,
      suggestions,
      timestamp: new Date().toISOString()
    };

    // 6. Record and potentially notify
    this.ledger.logDecision(intent, decision);
    
    if (status !== "COMMIT") {
        this.notifier.notify(intent, decision).catch(console.error);
    }

    return decision;
  }
}
