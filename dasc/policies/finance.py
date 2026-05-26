from ..schemas import Intent

def finance_policy(intent: Intent):
    """
    Finance Policy
    Focuses on spending limits, duplicate transaction detection, and account verification.
    """
    payload = getattr(intent, "payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}

    amount = payload.get("amount")
    currency = payload.get("currency")
    transaction_type = payload.get("transaction_type")

    # 1. Hard spending limit for ANY agent without manual escalation
    if amount and isinstance(amount, (int, float)) and amount > 5000 and intent.risk_tier < 4:
        return False, "TRANSACTION_LIMIT_EXCEEDED: Amounts > 5000 require Risk Tier 4 (Mandatory Escalation)"

    # 2. Prevent transfers to unverified accounts
    if transaction_type == "TRANSFER" and not payload.get("recipient_verified"):
        return False, "UNVERIFIED_RECIPIENT: Transfers only allowed to verified accounts"

    # 3. Currency restriction (e.g. no crypto for base agents)
    if currency in ["BTC", "ETH"]:
        if "crypto-specialist" not in intent.actor_agent.lower():
            return False, "CURRENCY_RESTRICTION: Agent not authorized for crypto transactions"

    return True, ""
