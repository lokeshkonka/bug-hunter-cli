import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path

class BaseStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    @asynccontextmanager
    async def transaction(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
