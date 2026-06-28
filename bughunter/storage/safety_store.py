from typing import Optional, List, Dict, Any
from bughunter.storage.base import BaseStore
import uuid
from datetime import datetime, timezone

class SafetyStore(BaseStore):
    async def log_security_event(
        self,
        run_id: str,
        event_type: str,
        pattern: str,
        confidence: str,
        content_hash: str,
        action_taken: str,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None
    ):
        event_id = str(uuid.uuid4())
        detected_at = datetime.now(timezone.utc).isoformat()
        
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO security_events (
                    id, run_id, event_type, source_file, source_line,
                    pattern, confidence, content_hash, detected_at, action_taken
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, run_id, event_type, source_file, source_line,
                    pattern, confidence, content_hash, detected_at, action_taken
                )
            )
