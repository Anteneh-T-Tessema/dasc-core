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
                    timestamp TEXT,
                    previous_hash TEXT,
                    record_hash TEXT
                )
            """)

    def _get_last_hash(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT record_hash FROM decisions ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else "0" * 64

    def log_decision(self, intent: Intent, decision: Decision):
        from .sanitizer import sanitize_content
        from .utils import calculate_string_hash
        
        # Security: Scrub sensitive data from the intent JSON
        sanitized_intent_json = sanitize_content(intent.model_dump_json())
        prev_hash = self._get_last_hash()
        
        # Integrity: Calculate hash for this record including the previous hash
        record_content = f"{intent.intent_id}{decision.status}{sanitized_intent_json}{decision.timestamp}{prev_hash}"
        current_hash = calculate_string_hash(record_content)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO decisions (intent_id, actor_agent, status, reason_codes, intent_json, timestamp, previous_hash, record_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intent.intent_id,
                intent.actor_agent,
                decision.status,
                json.dumps(decision.reason_codes),
                sanitized_intent_json,
                decision.timestamp,
                prev_hash,
                current_hash
            ))
        print(f"[LEDGER] Recorded: {decision.status} for {intent.intent_id} (Hash: {current_hash[:8]})")

    def verify_integrity(self) -> bool:
        """
        Verifies the hash-chain integrity of the entire ledger.
        Returns False if any tampering is detected.
        """
        from .utils import calculate_string_hash
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM decisions ORDER BY id ASC")
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            expected_prev_hash = "0" * 64
            for row in rows:
                if row['previous_hash'] != expected_prev_hash:
                    return False
                
                # Re-calculate hash
                content = f"{row['intent_id']}{row['status']}{row['intent_json']}{row['timestamp']}{row['previous_hash']}"
                actual_hash = calculate_string_hash(content)
                if actual_hash != row['record_hash']:
                    return False
                
                expected_prev_hash = actual_hash
        return True

    def get_history(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM decisions ORDER BY timestamp DESC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
