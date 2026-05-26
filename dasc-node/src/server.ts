import Fastify from "fastify";
import cors from "@fastify/cors";
import { Kernel } from "./kernel.js";
import { Intent } from "./types.js";
import { cybersecurityPolicy } from "./policies/cybersecurity.js";
import { financePolicy } from "./policies/finance.js";
import { healthcarePolicy } from "./policies/healthcare.js";
import fastifyWebsocket from "@fastify/websocket";
import "dotenv/config";

const fastify = Fastify({ 
  logger: {
    level: 'info',
    transport: {
      target: 'pino-pretty'
    }
  } 
});

const kernel = new Kernel({ 
  "config.json": "v1.0.0",
  "dasc-node": "v1.0.0" 
});

// Register Policies
kernel.registerPolicy(cybersecurityPolicy);
kernel.registerPolicy(financePolicy);
kernel.registerPolicy(healthcarePolicy);

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
