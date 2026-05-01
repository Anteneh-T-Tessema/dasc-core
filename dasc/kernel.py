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
        # Policy Registry: List of callable functions (intent) -> (bool, str)
        self.policies = []

    def register_policy(self, policy_func):
        """Registers a custom policy function."""
        self.policies.append(policy_func)
        logger.info(f"Registered custom policy: {policy_func.__name__}")

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

        # 4. Custom Registered Policies
        for policy in self.policies:
            try:
                pass_check, reason = policy(intent)
                if not pass_check:
                    reasons.append(f"CUSTOM_POLICY_VIOLATION: {reason}")
                    logger.warning(f"[{intent.intent_id}] Custom policy '{policy.__name__}' failed: {reason}")
            except Exception as e:
                logger.error(f"Error executing custom policy '{policy.__name__}': {str(e)}")
                reasons.append(f"POLICY_EXECUTION_ERROR: {policy.__name__}")

        # 5. Formulate Decision & Suggestions
        status = "COMMIT"
        if reasons:
            status = "ESCALATE" if any("TIER_4" in r for r in reasons) else "REJECT"
        elif intent.risk_tier == 4:
            status = "ESCALATE"
            reasons = ["TIER_4_MANDATORY_ESCALATION"]

        suggestions = []
        if status != "COMMIT":
            if "MISSING_COMPENSATION_PLAN_FOR_HIGH_RISK" in reasons:
                suggestions.append("Provide a 'compensation_plan' (e.g. {'undo': 'revert_action'}) for high-risk actions.")
            if any("OCC" in r for r in reasons):
                suggestions.append("The target artifact has changed. Fetch the latest state version/hash and resubmit.")
            if status == "ESCALATE":
                suggestions.append("Human approval required. Monitor the DASC Control Plane for decision status.")

        decision = Decision(
            intent_id=intent.intent_id,
            status=status,
            reason_codes=reasons,
            suggestions=suggestions
        )

        if status == "COMMIT":
            logger.info(f"[{intent.intent_id}] COMMITTED successfully.")
        elif status == "ESCALATE":
            logger.info(f"[{intent.intent_id}] ESCALATED for human approval.")
        else:
            logger.error(f"[{intent.intent_id}] REJECTED. Reasons: {reasons}")

        # 6. Record and potentially raise
        self.ledger.log_decision(intent, decision)

        if raise_on_failure and status != "COMMIT":
            if status == "ESCALATE":
                raise EscalationRequired("Human gate required", intent_id=intent.intent_id)
            error_cls = next((error_map[r.split(":")[0]] for r in reasons if r.split(":")[0] in error_map), DASCError)
            raise error_cls(str(reasons), intent_id=intent.intent_id)

        return decision
