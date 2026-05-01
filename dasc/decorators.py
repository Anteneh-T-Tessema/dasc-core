import functools
import uuid
from typing import Dict, Any, Optional
from .kernel import Kernel
from .schemas import Intent

def dasc_gate(
    kernel: Kernel, 
    risk_tier: int = 1, 
    action_type: Optional[str] = None,
    target_artifact: Optional[str] = None
):
    """
    A decorator that intercepts function calls and validates them 
    against the DASC kernel before execution.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Automagically determine metadata if not provided
            act_type = action_type or f"call_{func.__name__}"
            target = target_artifact or (args[0] if args else "unknown_target")
            
            # 2. Build the intent from function context
            intent = Intent(
                intent_id=f"INT-{uuid.uuid4().hex[:8].upper()}",
                actor_agent="decorated_function",
                action_type=act_type,
                target_artifact=str(target),
                risk_tier=risk_tier
            )
            
            # 3. Evaluate through the kernel (raise_on_failure=True for easy DX)
            kernel.evaluate(intent, raise_on_failure=True)
            
            # 4. If we reach here, it's a COMMIT
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Example Usage:
# @dasc_gate(kernel, risk_tier=2)
# def update_database(record_id, data):
#     ...
