from typing import Optional, List
from bughunter.storage.base import BaseStore
from bughunter.models.run import Run, RunStatus

class RunStore(BaseStore):
    async def create_run(self, run: Run) -> Run:
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO runs (id, status, scope_path, created_at, completed_at, token_budget, cost_budget_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.status.value,
                    run.scope_path,
                    run.created_at,
                    run.completed_at,
                    run.token_budget,
                    run.cost_budget_usd
                )
            )
        return run

    async def get_run(self, run_id: str) -> Optional[Run]:
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Run(
                        id=row["id"],
                        status=RunStatus(row["status"]),
                        scope_path=row["scope_path"],
                        created_at=row["created_at"],
                        completed_at=row["completed_at"],
                        token_budget=row["token_budget"],
                        cost_budget_usd=row["cost_budget_usd"]
                    )
        return None

    async def update_run_status(self, run_id: str, status: RunStatus, completed_at: Optional[str] = None):
        async with self.transaction() as conn:
            if completed_at:
                await conn.execute(
                    "UPDATE runs SET status = ?, completed_at = ? WHERE id = ?",
                    (status.value, completed_at, run_id)
                )
            else:
                await conn.execute(
                    "UPDATE runs SET status = ? WHERE id = ?",
                    (status.value, run_id)
                )
