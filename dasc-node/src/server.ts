import Fastify from "fastify";
import cors from "@fastify/cors";
import { Kernel } from "./kernel.js";
import { Intent } from "./types.js";
import { cybersecurityPolicy } from "./policies/cybersecurity.js";
import { financePolicy } from "./policies/finance.js";
import { healthcarePolicy } from "./policies/healthcare.js";
import { privacyPolicy } from "./policies/privacy.js";
import fastifyWebsocket from "@fastify/websocket";
import "dotenv/config";
import * as path from "path";

const fastify = Fastify({ 
  logger: {
    level: 'info',
    transport: {
      target: 'pino-pretty'
    }
  } 
});

import { DeclarativePolicyEngine } from "./policies/declarative.js";
import * as fs from "fs";

const kernel = new Kernel({ 
  "config.json": "v1.0.0",
  "dasc-node": "v1.0.0" 
});

// Register Policies
kernel.registerPolicy(cybersecurityPolicy);
kernel.registerPolicy(financePolicy);
kernel.registerPolicy(healthcarePolicy);
kernel.registerPolicy(privacyPolicy);

// Declarative Policy Engine configuration
const RULES_FILE = process.env.DASC_RULES_FILE || "dasc_rules.json";
const RULES_DIR = process.env.DASC_RULES_DIR || "dasc_rules.d";
const POLICIES_DIR = process.env.DASC_POLICIES_DIR || "dasc_policies.d";
const declarativeEngine = new DeclarativePolicyEngine();

if (fs.existsSync(RULES_FILE)) {
  try {
    declarativeEngine.loadRulesFromFile(RULES_FILE);
    console.log(`[DASC] Loaded ${declarativeEngine.rules.length} declarative rules from ${RULES_FILE}`);
  } catch (err: any) {
    console.error(`[DASC] Error loading declarative rules: ${err.message}`);
  }
} else {
  const defaultRules = {
    rules: [
      {
        name: "Limit Big Spends",
        condition: "payload.amount > 1000 and risk_tier < 3",
        action: "REJECT",
        reason: "TOO_EXPENSIVE"
      },
      {
        name: "Nuke Command Verification",
        condition: "action_type == 'NUKE'",
        action: "ESCALATE",
        reason: "NUKE_COMMAND_HITL"
      }
    ]
  };
  try {
    fs.writeFileSync(RULES_FILE, JSON.stringify(defaultRules, null, 2), "utf-8");
    declarativeEngine.loadRulesFromFile(RULES_FILE);
    console.log(`[DASC] Created and loaded default rules at ${RULES_FILE}`);
  } catch (err: any) {
    console.error(`[DASC] Error writing default rules file: ${err.message}`);
  }
}

if (fs.existsSync(RULES_DIR) && fs.statSync(RULES_DIR).isDirectory()) {
  try {
    declarativeEngine.loadRulesFromDirectory(RULES_DIR);
    console.log(`[DASC] Loaded additional declarative rules from folder ${RULES_DIR}. Total rules: ${declarativeEngine.rules.length}`);
  } catch (err: any) {
    console.error(`[DASC] Error loading rules from directory ${RULES_DIR}: ${err.message}`);
  }
}

kernel.registerPolicy(declarativeEngine.evaluatePolicies);

// Load Dynamic Imperative Policies (TS/JS)
if (fs.existsSync(POLICIES_DIR) && fs.statSync(POLICIES_DIR).isDirectory()) {
  console.log(`[DASC] Scanning imperative policies directory: ${POLICIES_DIR}`);
  try {
    const files = fs.readdirSync(POLICIES_DIR);
    for (const file of files) {
      if ((file.endsWith(".js") || file.endsWith(".ts")) && !file.startsWith("_")) {
        const filePath = path.resolve(POLICIES_DIR, file);
        try {
          const moduleUrl = `file://${filePath}`;
          const module = await import(moduleUrl);
          for (const [key, value] of Object.entries(module)) {
            if (typeof value === "function" && key.endsWith("Policy")) {
              kernel.registerPolicy(value as any);
              console.log(`[DASC] Registered dynamic imperative policy: ${key} (from ${file})`);
            }
          }
        } catch (err: any) {
          console.error(`[DASC] Error loading dynamic policy from ${file}: ${err.message}`);
        }
      }
    }
  } catch (err: any) {
    console.error(`[DASC] Error reading policies directory ${POLICIES_DIR}: ${err.message}`);
  }
}

await fastify.register(cors, {
  origin: true // In production, restrict this
});

await fastify.register(fastifyWebsocket);

const activeSockets = new Set<any>();

function broadcast(message: any) {
  const payload = JSON.stringify(message);
  for (const socket of activeSockets) {
    try {
      socket.send(payload);
    } catch (err) {
      activeSockets.delete(socket);
    }
  }
}

// --- Middleware: API Key Auth ---
fastify.addHook("preHandler", async (request, reply) => {
  if (request.url === "/health" || request.url.startsWith("/ws")) return;
  
  const apiKey = request.headers["x-api-key"];
  if (!apiKey || apiKey !== process.env.DASC_API_KEY) {
    reply.status(401).send({ error: "Unauthorized: Invalid or missing DASC API Key" });
  }
});

// Health check
fastify.get("/health", async () => ({ 
  status: "ok", 
  version: "1.0.0",
  timestamp: new Date().toISOString()
}));

// Get full ledger (Audit Trail) with time-travel query support
fastify.get("/ledger", async (request) => {
  const { limit, as_of } = request.query as { limit?: string; as_of?: string };
  if (as_of) {
    return (kernel as any).ledger.getHistoryAsOf(as_of, limit ? parseInt(limit) : 100);
  }
  return kernel["ledger"].getHistory(limit ? parseInt(limit) : 100);
});

// Evaluate Intent (The Safety Gate)
fastify.post("/evaluate", async (request, reply) => {
  const intent = request.body as Intent;
  
  if (!intent.intent_id || !intent.actor_agent) {
    return reply.status(400).send({ error: "Invalid intent: Missing intent_id or actor_agent" });
  }

  const decision = kernel.evaluate(intent);
  fastify.log.info({ intent_id: intent.intent_id, status: decision.status }, "Intent Evaluated");
  
  broadcast({
    type: "INTENT_EVALUATED",
    intent,
    decision
  });
  
  return decision;
});

// HITL Approval (Human-in-the-loop)
fastify.post("/approve", async (request, reply) => {
  const { intent_id, approved, approver, approver_id } = request.body as any;
  const activeApprover = approver || approver_id;
  
  if (!intent_id || approved === undefined || !activeApprover) {
    return reply.status(400).send({ error: "Missing required fields: intent_id, approved, approver or approver_id" });
  }

  try {
    const decision = await kernel.approveIntent(intent_id, approved, activeApprover);
    fastify.log.info({ intent_id, approved, approver: activeApprover }, "HITL Decision Applied");
    
    broadcast({
      type: "DECISION_UPDATED",
      intent_id,
      status: decision.status,
      decision
    });
    
    return decision;
  } catch (err: any) {
    reply.status(400).send({ error: err.message });
  }
});

// WebSocket connection route
fastify.get("/ws", { websocket: true }, (connection, req) => {
  activeSockets.add(connection.socket);
  
  connection.socket.on("message", async (message: string) => {
    try {
      const data = JSON.parse(message);
      if (data.type === "APPROVE" || data.type === "DENY") {
        const intent_id = data.intent_id;
        const approved = data.type === "APPROVE";
        const approver = data.approver || "DASC_ADMIN_WS";
        
        const decision = await kernel.approveIntent(intent_id, approved, approver);
        broadcast({
          type: "DECISION_UPDATED",
          intent_id,
          status: decision.status,
          decision
        });
      }
    } catch (err: any) {
      connection.socket.send(JSON.stringify({ type: "ERROR", message: err.message }));
    }
  });

  connection.socket.on("close", () => {
    activeSockets.delete(connection.socket);
  });
});

// Stats for Dashboard
fastify.get("/stats", async () => {
  const history = kernel["ledger"].getHistory(1000) as any[];
  return {
    total: history.length,
    commits: history.filter(h => h.status === "COMMIT").length,
    rejections: history.filter(h => h.status === "REJECT").length,
    escalations: history.filter(h => h.status === "ESCALATE").length,
    last_updated: new Date().toISOString()
  };
});

// GET /policies
fastify.get("/policies", async () => {
  return { rules: declarativeEngine.rules };
});

// POST /policies
fastify.post("/policies", async (request, reply) => {
  const rulesData = request.body as any;
  if (!rulesData || !Array.isArray(rulesData.rules)) {
    return reply.status(400).send({ error: "Invalid policies format: 'rules' list is required" });
  }

  for (const rule of rulesData.rules) {
    if (!rule.name || !rule.condition || !rule.action || !rule.reason) {
      return reply.status(400).send({ error: "Invalid rule structure. Each rule must have 'name', 'condition', 'action', and 'reason'" });
    }
    if (!["COMMIT", "REJECT", "ESCALATE"].includes(rule.action)) {
      return reply.status(400).send({ error: "Invalid action. Must be one of COMMIT, REJECT, ESCALATE" });
    }
  }

  try {
    fs.writeFileSync(RULES_FILE, JSON.stringify(rulesData, null, 2), "utf-8");
    declarativeEngine.loadRulesFromFile(RULES_FILE);
    return { status: "success", rules: declarativeEngine.rules };
  } catch (err: any) {
    return reply.status(500).send({ error: `Failed to save policies: ${err.message}` });
  }
});

// GET /export
fastify.get("/export", async (request, reply) => {
  const { format, as_of } = request.query as { format?: string; as_of?: string };
  let history: any[];
  
  if (as_of) {
    history = (kernel as any).ledger.getHistoryAsOf(as_of, 1000);
  } else {
    history = kernel["ledger"].getHistory(1000);
  }

  if (format === "csv") {
    let csv = "Namespace,Intent ID,Actor Agent,Status,Reason Codes,Timestamp,Previous Hash,Record Hash\n";
    for (const r of history) {
      const reasons = Array.isArray(r.reason_codes) ? r.reason_codes.join("; ") : String(r.reason_codes);
      const ns = r.namespace || "default";
      csv += `"${ns}","${r.intent_id}","${r.actor_agent}","${r.status}","${reasons}","${r.timestamp}","${r.previous_hash}","${r.record_hash}"\n`;
    }
    reply.header("Content-Type", "text/csv");
    reply.header("Content-Disposition", "attachment; filename=dasc_compliance_report.csv");
    return csv;
  } else if (format === "markdown") {
    const lines: string[] = [];
    lines.push("# DASC Compliance Security Audit Report");
    lines.push(`\n* **Generated**: ${new Date().toISOString()}`);
    if (as_of) {
      lines.push(`* **Bitemporal Cutoff (As Of)**: ${as_of}`);
    }
    const isIntact = (kernel as any).ledger.verifyIntegrity();
    lines.push(`* **Ledger Integrity Check**: ${isIntact ? "PASS" : "FAIL"}`);
    
    lines.push("\n## Audit Trail Summary");
    const total = history.length;
    const commits = history.filter(h => h.status === "COMMIT").length;
    const rejections = history.filter(h => h.status === "REJECT").length;
    const escalations = history.filter(h => h.status === "ESCALATE").length;
    
    lines.push(`* **Total Evaluated Intents**: ${total}`);
    lines.push(`* **Total Commits**:           ${commits}`);
    lines.push(`* **Total Rejections**:        ${rejections}`);
    lines.push(`* **Total Escalations**:       ${escalations}`);
    
    lines.push("\n## Ledger Records");
    lines.push("| Timestamp | Intent ID | Agent | Status | Reasons | Record Hash |");
    lines.push("| --- | --- | --- | --- | --- | --- |");
    for (const r of history) {
      const reasons = Array.isArray(r.reason_codes) ? r.reason_codes.join(", ") : String(r.reason_codes);
      lines.push(`| ${r.timestamp} | \`${r.intent_id}\` | \`${r.actor_agent}\` | **${r.status}** | ${reasons || "None"} | \`${r.record_hash.slice(0, 8)}\` |`);
    }
    
    reply.header("Content-Type", "text/markdown");
    reply.header("Content-Disposition", "attachment; filename=dasc_compliance_report.md");
    return lines.join("\n");
  } else {
    return { history };
  }
});

const start = async () => {
  const port = parseInt(process.env.DASC_PORT || "3000");
  const host = process.env.DASC_HOST || "0.0.0.0";
  
  try {
    await fastify.listen({ port, host });
    console.log(`\n🚀 DASC-Core Node Server running on http://${host}:${port}`);
    console.log(`🔐 API Key protection active\n`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
