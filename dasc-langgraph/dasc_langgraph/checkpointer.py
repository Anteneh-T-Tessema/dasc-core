import sqlite3
from typing import Optional, Iterator, Tuple, Dict, Any
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple, CheckpointMetadata

class DASCLangGraphCheckpointer(BaseCheckpointSaver):
    """
    DASCLangGraphCheckpointer
    A sqlite-backed LangGraph Checkpoint Saver that integrates with the DASC bitemporal ledger.
    Stores agent states and links execution checkpoints to safety records.
    """
    def __init__(self, db_path: str = "dasc_ledger.db"):
        super().__init__()
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
                    thread_id TEXT,
                    checkpoint_id TEXT,
                    parent_id TEXT,
                    checkpoint_format TEXT,
                    checkpoint_bytes BLOB,
                    metadata_format TEXT,
                    metadata_bytes BLOB,
                    timestamp TEXT,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple by thread_id and checkpoint_id."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with sqlite3.connect(self.db_path) as conn:
            if checkpoint_id:
                cursor = conn.execute(
                    "SELECT parent_id, checkpoint_format, checkpoint_bytes, metadata_format, metadata_bytes FROM langgraph_checkpoints WHERE thread_id = ? AND checkpoint_id = ?",
                    (thread_id, checkpoint_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT parent_id, checkpoint_format, checkpoint_bytes, metadata_format, metadata_bytes, checkpoint_id FROM langgraph_checkpoints WHERE thread_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (thread_id,)
                )
            row = cursor.fetchone()
            if not row:
                return None

            if checkpoint_id:
                parent_id, chk_fmt, chk_bytes, meta_fmt, meta_bytes = row
            else:
                parent_id, chk_fmt, chk_bytes, meta_fmt, meta_bytes, checkpoint_id = row

            # Deserialize using loads_typed
            checkpoint = self.serde.loads_typed((chk_fmt, chk_bytes))
            metadata = self.serde.loads_typed((meta_fmt, meta_bytes)) if meta_bytes else {}

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint_id
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": parent_id
                    }
                } if parent_id else None
            )

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: Any = None) -> Dict[str, Any]:
        """Save a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        parent_id = config["configurable"].get("checkpoint_id")

        chk_fmt, chk_bytes = self.serde.dumps_typed(checkpoint)
        meta_fmt, meta_bytes = self.serde.dumps_typed(metadata)
        timestamp = checkpoint.get("ts") or checkpoint.get("timestamp") or ""

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO langgraph_checkpoints (thread_id, checkpoint_id, parent_id, checkpoint_format, checkpoint_bytes, metadata_format, metadata_bytes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, checkpoint_id, parent_id, chk_fmt, chk_bytes, meta_fmt, meta_bytes, timestamp)
            )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }

    def list(self, config: Dict[str, Any], *, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, filter: Optional[Dict[str, Any]] = None) -> Iterator[CheckpointTuple]:
        """List checkpoints for a thread."""
        thread_id = config["configurable"]["thread_id"]
        query = "SELECT parent_id, checkpoint_format, checkpoint_bytes, metadata_format, metadata_bytes, checkpoint_id FROM langgraph_checkpoints WHERE thread_id = ?"
        params = [thread_id]

        if before:
            query += " AND timestamp < ?"
            params.append(before["configurable"]["checkpoint_id"])

        query += " ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                parent_id, chk_fmt, chk_bytes, meta_fmt, meta_bytes, checkpoint_id = row
                checkpoint = self.serde.loads_typed((chk_fmt, chk_bytes))
                metadata = self.serde.loads_typed((meta_fmt, meta_bytes)) if meta_bytes else {}
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": checkpoint_id
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": parent_id
                        }
                    } if parent_id else None
                )
