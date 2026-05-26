import { Intent } from "../types.js";

/**
 * Cybersecurity Policy Adapter
 * Focuses on preventing Command Injection and Unauthorized Path Access.
 */
export const cybersecurityPolicy = (intent: Intent): { pass: boolean; reason?: string } => {
  const dangerousCommands = ["rm -rf", "mkfs", "dd", "sh ", "bash ", "curl ", "wget "];
  const restrictedPaths = ["/etc/shadow", "/etc/passwd", "~/.ssh", "/var/run/docker.sock"];

  const payloadString = JSON.stringify(intent.payload).toLowerCase();

  // 1. Check for dangerous shell commands
  for (const cmd of dangerousCommands) {
    if (payloadString.includes(cmd)) {
      return { pass: false, reason: `DANGEROUS_COMMAND_DETECTED: ${cmd}` };
    }
  }

  // 2. Check for restricted system paths
  for (const path of restrictedPaths) {
    if (payloadString.includes(path)) {
      return { pass: false, reason: `RESTRICTED_PATH_ACCESS: ${path}` };
    }
  }

  // 3. Prevent Tier 1 agents from doing Tier 3+ actions
  if (intent.actor_agent.includes("untrusted") && intent.risk_tier >= 3) {
    return { pass: false, reason: "PRIVILEGE_MISMATCH: Untrusted agent attempted Tier 3 action" };
  }

  return { pass: true };
};
