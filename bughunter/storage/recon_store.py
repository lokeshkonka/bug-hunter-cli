from typing import Optional, List, Dict, Any
from bughunter.storage.base import BaseStore

class ReconStore(BaseStore):
    async def insert_file(self, file_id: str, run_id: str, path: str, language: str, relevance_score: float, excluded: bool, excluded_reason: str):
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO files (id, run_id, path, language, relevance_score, excluded, excluded_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, run_id, path, language, relevance_score, int(excluded), excluded_reason)
            )

    async def insert_index_entry(self, entry_id: str, run_id: str, file_id: str, symbol: str, line_start: int, line_end: int, security_relevance: str, tags: str, test_category: str):
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO index_entries (id, run_id, file_id, symbol, line_start, line_end, security_relevance, tags, test_category, semgrep_rule_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, run_id, file_id, symbol, line_start, line_end, security_relevance, tags, test_category, "[]")
            )
            
    async def update_semgrep_rules(self, entry_id: str, rules_json: str):
        async with self.transaction() as conn:
            await conn.execute("UPDATE index_entries SET semgrep_rule_ids = ? WHERE id = ?", (rules_json, entry_id))
            
    async def get_index_entries_by_tags(self, run_id: str, tags: List[str]) -> List[Dict[str, Any]]:
        # This gets entries that have any of the given tags
        entries = []
        async with self.get_connection() as conn:
            async with conn.execute("SELECT e.*, f.path as file_path, f.relevance_score FROM index_entries e JOIN files f ON e.file_id = f.id WHERE e.run_id = ?", (run_id,)) as cursor:
                async for row in cursor:
                    entry_tags = row["tags"].split(",") if row["tags"] else []
                    if any(t in entry_tags for t in tags):
                        entries.append(dict(row))
        return entries
