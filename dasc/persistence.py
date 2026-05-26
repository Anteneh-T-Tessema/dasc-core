import json
import logging
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .schemas import Intent, Decision
from .sanitizer import sanitize_content
from .utils import calculate_string_hash

Base = declarative_base()

class DecisionRecord(Base):
    __tablename__ = 'dasc_decisions'
    id = Column(Integer, primary_key=True)
    namespace = Column(String(50), default="default", index=True)
    intent_id = Column(String(50))
    actor_agent = Column(String(100))
    status = Column(String(20))
    reason_codes = Column(Text)
    intent_json = Column(Text)
    timestamp = Column(String(50))
    previous_hash = Column(String(64))
    record_hash = Column(String(64))

class PostgresLedger:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _get_last_hash(self, session, namespace: str = "default"):
        last = session.query(DecisionRecord).filter_by(namespace=namespace).order_by(DecisionRecord.id.desc()).first()
        return last.record_hash if last else "0" * 64

    def log_decision(self, intent: Intent, decision: Decision):
        sanitized_intent_json = sanitize_content(intent.model_dump_json())
        
        with self.Session() as session:
            prev_hash = self._get_last_hash(session, intent.namespace)
            
            # Integrity Hash (including namespace now)
            record_content = f"{intent.namespace}{intent.intent_id}{decision.status}{sanitized_intent_json}{decision.timestamp}{prev_hash}"
            current_hash = calculate_string_hash(record_content)
            
            record = DecisionRecord(
                namespace=intent.namespace,
                intent_id=intent.intent_id,
                actor_agent=intent.actor_agent,
                status=decision.status,
                reason_codes=json.dumps(decision.reason_codes),
                intent_json=sanitized_intent_json,
                timestamp=decision.timestamp,
                previous_hash=prev_hash,
                record_hash=current_hash
            )
            session.add(record)
            session.commit()
            print(f"[POSTGRES LEDGER] Recorded: {decision.status} for {intent.intent_id} in {intent.namespace}")

    def get_history(self, namespace: Optional[str] = None):
        with self.Session() as session:
            query = session.query(DecisionRecord)
            if namespace:
                query = query.filter_by(namespace=namespace)
            rows = query.order_by(DecisionRecord.id.desc()).all()
            return [
                {
                    "namespace": r.namespace,
                    "intent_id": r.intent_id,
                    "actor_agent": r.actor_agent,
                    "status": r.status,
                    "reason_codes": json.loads(r.reason_codes),
                    "intent_json": r.intent_json,
                    "timestamp": r.timestamp,
                    "previous_hash": r.previous_hash,
                    "record_hash": r.record_hash
                } for r in rows
            ]

    def get_history_as_of(self, timestamp: str, namespace: Optional[str] = None):
        with self.Session() as session:
            query = session.query(DecisionRecord).filter(DecisionRecord.timestamp <= timestamp)
            if namespace:
                query = query.filter_by(namespace=namespace)
            rows = query.order_by(DecisionRecord.id.desc()).all()
            return [
                {
                    "namespace": r.namespace,
                    "intent_id": r.intent_id,
                    "actor_agent": r.actor_agent,
                    "status": r.status,
                    "reason_codes": json.loads(r.reason_codes),
                    "intent_json": r.intent_json,
                    "timestamp": r.timestamp,
                    "previous_hash": r.previous_hash,
                    "record_hash": r.record_hash
                } for r in rows
            ]

    def verify_integrity(self) -> bool:
        with self.Session() as session:
            records = session.query(DecisionRecord).order_by(DecisionRecord.id.asc()).all()
            expected_prev_hash = "0" * 64
            for r in records:
                if r.previous_hash != expected_prev_hash:
                    return False
                content = f"{r.intent_id}{r.status}{r.intent_json}{r.timestamp}{r.previous_hash}"
                if calculate_string_hash(content) != r.record_hash:
                    return False
                expected_prev_hash = r.record_hash
        return True
