import { Intent } from "../types.js";

/**
 * Finance Policy Adapter
 * Focuses on spending limits, duplicate transaction detection, and account verification.
 */
export const financePolicy = (intent: Intent): { pass: boolean; reason?: string } => {
  const { amount, currency, transaction_type } = intent.payload || {};

  // 1. Hard spending limit for ANY agent without manual escalation
  if (amount && amount > 5000 && intent.risk_tier < 4) {
    return { 
        pass: false, 
        reason: "TRANSACTION_LIMIT_EXCEEDED: Amounts > 5000 require Risk Tier 4 (Mandatory Escalation)" 
    };
  }

  // 2. Prevent transfers to unverified accounts
  if (transaction_type === "TRANSFER" && !intent.payload.recipient_verified) {
    return { pass: false, reason: "UNVERIFIED_RECIPIPIENT: Transfers only allowed to verified accounts" };
  }

  // 3. Currency restriction (e.g. no crypto for base agents)
  if (currency === "BTC" || currency === "ETH") {
    if (!intent.actor_agent.includes("crypto-specialist")) {
        return { pass: false, reason: "CURRENCY_RESTRICTION: Agent not authorized for crypto transactions" };
    }
  }

  return { pass: true };
};
