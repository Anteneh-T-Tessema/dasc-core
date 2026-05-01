import sqlite3
import json
import datetime
from .schemas import Decision, Intent

class BitemporalLedger:
    def __init__(self, db_path="dasc_ledger.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT,
                    actor_agent TEXT,
                    status TEXT,
                    reason_codes TEXT,
                    intent_json TEXT,
                    timestamp TEXT
                )
            """)

    def log_decision(self, intent: Intent, decision: Decision):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO decisions (intent_id, actor_agent, status, reason_codes, intent_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                intent.intent_id,
                intent.actor_agent,
                decision.status,
                json.dumps(decision.reason_codes),
                intent.model_dump_json(),
                decision.timestamp
            ))
        print(f"[LEDGER] Recorded: {decision.status} for {intent.intent_id} in SQLite")

    def get_history(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM decisions ORDER BY timestamp DESC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
