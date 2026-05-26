import json
from ..schemas import Intent

def get_field_value(obj, field_path: str):
    """
    Safely resolves a nested field value from an object/dict.
    e.g., 'payload.amount' -> obj.payload.get('amount')
    """
    parts = field_path.strip().split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current

def parse_val(val_str: str):
    """
    Parses string value to its literal type (bool, int, float, str).
    """
    val_str = val_str.strip()
    if val_str.lower() == "true":
        return True
    if val_str.lower() == "false":
        return False
    if (val_str.startswith("'") and val_str.endswith("'")) or (val_str.startswith('"') and val_str.endswith('"')):
        return val_str[1:-1]
    
    # Try parsing as float/int
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str

def evaluate_comparison(left, op: str, right_str: str) -> bool:
    """
    Evaluates a single binary operator comparison.
    """
    if left is None:
        if op == "!=":
            return True
        return False

    right = parse_val(right_str)
    
    # Cast types if necessary for numeric comparisons
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left = float(left)
        right = float(right)

    if op == "==":
        return left == right
    elif op == "!=":
        return left != right
    elif op == ">=":
        return left >= right
    elif op == "<=":
        return left <= right
    elif op == ">":
        return left > right
    elif op == "<":
        return left < right
    elif op == "contains":
        return str(right) in str(left)
    elif op == "in":
        # right could be a comma-separated string or list representation
        if isinstance(right, str):
            items = [item.strip().strip("'").strip('"') for item in right.replace("[", "").replace("]", "").split(",")]
            return str(left) in items
        return left in right
    return False

def evaluate_condition(intent: Intent, condition_str: str) -> bool:
    """
    Evaluates a compound condition string (split by ' and ') on an intent.
    Example: 'payload.amount > 1000 and risk_tier < 3'
    """
    comparisons = condition_str.split(" and ")
    operators = ["==", "!=", ">=", "<=", ">", "<", " contains ", " in "]
    
    for comp in comparisons:
        comp = comp.strip()
        matched = False
        for op in operators:
            if op in comp:
                left_path, right_str = comp.split(op, 1)
                left_val = get_field_value(intent, left_path.strip())
                if not evaluate_comparison(left_val, op.strip(), right_str.strip()):
                    return False
                matched = True
                break
        if not matched:
            # If no operator is found, check truthiness of the field
            left_val = get_field_value(intent, comp)
            if not left_val:
                return False
    return True

class DeclarativePolicyEngine:
    """
    Loads and runs safety rules defined in JSON config structures.
    """
    def __init__(self, rules_json: dict = None):
        self.rules = rules_json.get("rules", []) if rules_json else []

    def load_rules_from_file(self, file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)
            self.rules = data.get("rules", [])

    def evaluate_policies(self, intent: Intent):
        """
        Policy evaluator conforming to DASC's custom policy signature: (intent) -> (pass, reason)
        """
        for rule in self.rules:
            condition = rule.get("condition")
            if condition:
                try:
                    if evaluate_condition(intent, condition):
                        action = rule.get("action", "REJECT")
                        reason = rule.get("reason", "DECLARATIVE_POLICY_VIOLATION")
                        # If action is ESCALATE, we can append 'TIER_4' to reason to trigger escalation
                        # or prepend TIER_4 to make DASC kernel elevate to ESCALATE status
                        if action == "ESCALATE":
                            reason = f"TIER_4_MANDATORY_ESCALATION: {reason}"
                        return False, reason
                except Exception as e:
                    # Ignore syntax errors in rule definitions, log warning or fail safe
                    return False, f"RULE_EVALUATION_ERROR: {rule.get('name')} ({str(e)})"
        return True, ""
