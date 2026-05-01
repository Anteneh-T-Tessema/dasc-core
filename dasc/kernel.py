import logging
from .schemas import Intent, Decision
from .ledger import BitemporalLedger
from .exceptions import (
    DASCError,
    OCCConflictError, 
    PolicyViolationError, 
    TaintDetectedError, 
    EscalationRequired
)

# Configure logging for production-ready observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DASC - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dasc")

class Kernel:
    def __init__(self, current_state_versions: dict = None):
        self.ledger = BitemporalLedger()
        # Mocking the current state of the world for OCC checks
        self.current_state_versions = current_state_versions or {}

    def evaluate(self, intent: Intent, raise_on_failure: bool = False) -> Decision:
        reasons = []
        error_map = {
            "IFC_TAINT_DETECTED": TaintDetectedError,
            "OCC_CONFLICT": OCCConflictError,
            "OCC_HASH_CONFLICT": OCCConflictError,
            "MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK": PolicyViolationError,
            "TIER_4_MANDATORY_ESCALATION": EscalationRequired
        }

        logger.info(f"Evaluating Intent {intent.intent_id} from agent {intent.actor_agent}")

        # 1. IFC / Taint Check
        for ev in intent.evidence:
            if ev.source_type == "untrusted" and intent.risk_tier >= 2:
                msg = f"IFC_TAINT_DETECTED: Untrusted evidence for sensitive action (Tier {intent.risk_tier})"
                reasons.append(msg)
                logger.warning(f"[{intent.intent_id}] {msg}")

        # 2. OCC / TOCTOU Check
        if intent.state_version_vector:
            from .utils import calculate_file_hash
            for artifact, version in intent.state_version_vector.items():
                current_v = self.current_state_versions.get(artifact)
                
                # If version is prefixed with 'hash:', calculate the actual file hash
                if version.startswith("hash:"):
                    expected_hash = version.split("hash:")[1]
                    actual_hash = calculate_file_hash(artifact)
                    if actual_hash and actual_hash != expected_hash:
                        msg = f"OCC_HASH_CONFLICT: {artifact} content changed. Expected {expected_hash[:8]}, got {actual_hash[:8]}"
                        reasons.append(msg)
                        logger.warning(f"[{intent.intent_id}] {msg}")
                elif current_v and current_v != version:
                    msg = f"OCC_CONFLICT: {artifact} changed from {version} to {current_v}"
                    reasons.append(msg)
                    logger.warning(f"[{intent.intent_id}] {msg}")

        # 3. Risk Tier Policy Check
        if intent.risk_tier >= 3 and not intent.compensation_plan:
            msg = "MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK"
            reasons.append(msg)
            logger.warning(f"[{intent.intent_id}] {msg}")

        # 4. Formulate Decision
        if reasons:
            decision = Decision(intent_id=intent.intent_id, status="REJECT", reason_codes=reasons)
            logger.error(f"[{intent.intent_id}] REJECTED. Reasons: {reasons}")
            if raise_on_failure:
                # Raise the first encountered error type
                error_cls = next((error_map[r.split(":")[0]] for r in reasons if r.split(":")[0] in error_map), DASCError)
                raise error_cls(str(reasons), intent_id=intent.intent_id)
        elif intent.risk_tier == 4:
            decision = Decision(intent_id=intent.intent_id, status="ESCALATE", reason_codes=["TIER_4_MANDATORY_ESCALATION"])
            logger.info(f"[{intent.intent_id}] ESCALATED for human approval.")
            if raise_on_failure:
                raise EscalationRequired("Human gate required for Tier 4 action", intent_id=intent.intent_id)
        else:
            decision = Decision(intent_id=intent.intent_id, status="COMMIT")
            logger.info(f"[{intent.intent_id}] COMMITTED successfully.")

        # 5. Record and Return
        self.ledger.log_decision(intent, decision)
        return decision
