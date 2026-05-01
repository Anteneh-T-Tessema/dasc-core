from .schemas import Intent, Decision
from .ledger import BitemporalLedger

class Kernel:
    def __init__(self, current_state_versions: dict = None):
        self.ledger = BitemporalLedger()
        # Mocking the current state of the world for OCC checks
        self.current_state_versions = current_state_versions or {}

    def evaluate(self, intent: Intent) -> Decision:
        reasons = []

        # 1. Schema / Type Check (Implicitly handled by Pydantic, but can add custom logic)
        
        # 2. Information Flow Control (IFC) / Taint Check
        # Example: Reject if evidence contains 'untrusted' source_type for high-tier actions
        for ev in intent.evidence:
            if ev.source_type == "untrusted" and intent.risk_tier >= 2:
                reasons.append("IFC_TAINT_DETECTED: Untrusted evidence for sensitive action")

        # 3. OCC / TOCTOU Check (Is the state the agent read still valid?)
        if intent.state_version_vector:
            for artifact, version in intent.state_version_vector.items():
                current_v = self.current_state_versions.get(artifact)
                if current_v and current_v != version:
                    reasons.append(f"OCC_CONFLICT: {artifact} changed from {version} to {current_v}")

        # 4. Risk Tier Policy Check
        if intent.risk_tier >= 3 and not intent.compensation_plan:
            reasons.append("MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK")

        # 5. Formulate Decision
        if reasons:
            decision = Decision(intent_id=intent.intent_id, status="REJECT", reason_codes=reasons)
        elif intent.risk_tier == 4:
            # Tier 4 always requires external escalation (Human-in-the-loop)
            decision = Decision(intent_id=intent.intent_id, status="ESCALATE", reason_codes=["TIER_4_MANDATORY_ESCALATION"])
        else:
            decision = Decision(intent_id=intent.intent_id, status="COMMIT")

        # 6. Record and Return
        self.ledger.log_decision(intent, decision)
        return decision
