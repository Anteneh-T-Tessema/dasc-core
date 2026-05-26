import Database from "better-sqlite3";
import { Intent, Decision } from "./types.js";
import * as crypto from "crypto";

export class BitemporalLedger {
  private db: Database.Database;

  constructor(dbPath: string = "dasc_ledger_node.db") {
    this.db = new Database(dbPath);
    this.init();
  }

  private init() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intent_id TEXT,
        actor_agent TEXT,
        status TEXT,
        reason_codes TEXT,
        intent_json TEXT,
        timestamp TEXT,
        previous_hash TEXT,
        record_hash TEXT
      )
    `);
  }

  private get_last_hash(): string {
    const row = this.db.prepare("SELECT record_hash FROM ledger ORDER BY id DESC LIMIT 1").get() as any;
    return row ? row.record_hash : "0".repeat(64);
  }

  private sanitize(content: string): string {
    // Basic PII scrubbing (SSN, Emails) for the audit trail
    return content
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, "[REDACTED_SSN]")
      .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, "[REDACTED_EMAIL]");
  }

  logDecision(intent: Intent, decision: Decision) {
    const prev_hash = this.get_last_hash();
    const intent_json = this.sanitize(JSON.stringify(intent));
    
    // Integrity: Calculate hash for this record including the previous hash
    const record_content = `${intent.intent_id}${decision.status}${intent_json}${decision.timestamp}${prev_hash}`;
    const record_hash = crypto.createHash("sha256").update(record_content).digest("hex");

    const stmt = this.db.prepare(`
      INSERT INTO ledger (intent_id, actor_agent, status, reason_codes, intent_json, timestamp, previous_hash, record_hash)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      intent.intent_id,
      intent.actor_agent,
      decision.status,
      JSON.stringify(decision.reason_codes),
      intent_json,
      decision.timestamp,
      prev_hash,
      record_hash
    );
    
    console.log(`[Ledger] Recorded ${decision.status} for ${intent.intent_id} (Hash: ${record_hash.slice(0, 8)})`);
  }

  getHistory(limit: number = 50) {
    return this.db.prepare("SELECT * FROM ledger ORDER BY id DESC LIMIT ?").all(limit);
  }

  getHistoryAsOf(timestamp: string, limit: number = 50) {
    return this.db.prepare("SELECT * FROM ledger WHERE timestamp <= ? ORDER BY id DESC LIMIT ?").all(timestamp, limit);
  }

  verifyIntegrity(): boolean {
    const rows = this.db.prepare("SELECT * FROM ledger ORDER BY id ASC").all() as any[];
    let expected_prev_hash = "0".repeat(64);

    for (const row of rows) {
      if (row.previous_hash !== expected_prev_hash) return false;
      
      const content = `${row.intent_id}${row.status}${row.intent_json}${row.timestamp}${row.previous_hash}`;
      const actual_hash = crypto.createHash("sha256").update(content).digest("hex");
      
      if (actual_hash !== row.record_hash) return false;
      expected_prev_hash = actual_hash;
    }
    return true;
  }
}
