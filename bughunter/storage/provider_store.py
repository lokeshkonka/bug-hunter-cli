from typing import Optional, List, Dict, Any
from bughunter.storage.base import BaseStore
import uuid
from datetime import datetime, timezone

class ProviderStore(BaseStore):
    async def log_usage(
        self, 
        run_id: str, 
        agent: str, 
        test_id: Optional[str], 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int, 
        estimated_cost_usd: float,
        cached: bool = False
    ):
        usage_id = str(uuid.uuid4())
        total_tokens = prompt_tokens + completion_tokens
        called_at = datetime.now(timezone.utc).isoformat()
        
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO provider_usage (
                    id, run_id, agent, test_id, model, 
                    prompt_tokens, completion_tokens, total_tokens, 
                    estimated_cost_usd, cached, called_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage_id, run_id, agent, test_id, model,
                    prompt_tokens, completion_tokens, total_tokens,
                    estimated_cost_usd, int(cached), called_at
                )
            )
            
    async def get_total_usage(self, run_id: str) -> Dict[str, Any]:
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT SUM(total_tokens) as total_tokens, SUM(estimated_cost_usd) as total_cost FROM provider_usage WHERE run_id = ?",
                (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return {
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost": row["total_cost"] or 0.0
                }
