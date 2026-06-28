from typing import Optional, List, Dict, Any
from bughunter.storage.base import BaseStore
import uuid
from datetime import datetime, timezone

class EvidenceStore(BaseStore):
    async def insert_evidence(
        self,
        run_id: str,
        test_plan_id: Optional[str],
        source_tool: str,
        source_file: str,
        line_start: int,
        line_end: int,
        observation: str,
        metadata: str
    ) -> str:
        evidence_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO evidence (
                    id, run_id, test_plan_id, source_tool, source_file,
                    line_start, line_end, observation, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id, run_id, test_plan_id, source_tool, source_file,
                    line_start, line_end, observation, metadata, created_at
                )
            )
        return evidence_id

    async def get_evidence_by_file(self, run_id: str, file_path: str) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM evidence WHERE run_id = ? AND source_file = ?", (run_id, file_path)) as cursor:
                return [dict(row) async for row in cursor]
