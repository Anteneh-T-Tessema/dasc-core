import { Intent, Decision } from "./types.js";

/**
 * Notification Manager
 * Sends alerts for REJECT or ESCALATE decisions to external webhooks (Slack, Teams).
 */
export class NotificationManager {
  private webhookUrl?: string;

  constructor(webhookUrl?: string) {
    this.webhookUrl = webhookUrl || process.env.DASC_WEBHOOK_URL;
  }

  async notify(intent: Intent, decision: Decision) {
    if (!this.webhookUrl) return;

    const payload = {
      text: `🚨 *DASC Safety Alert* 🚨\n*Status*: ${decision.status}\n*Agent*: ${intent.actor_agent}\n*Action*: ${intent.action_type}\n*Reasons*: ${decision.reason_codes.join(", ")}`,
      attachments: [{
          color: decision.status === "REJECT" ? "#FF0000" : "#FFA500",
          fields: [
              { title: "Intent ID", value: intent.intent_id, short: true },
              { title: "Risk Tier", value: intent.risk_tier.toString(), short: true }
          ]
      }]
    };

    try {
      await fetch(this.webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      console.error("[DASC] Failed to send notification:", err);
    }
  }
}
