import os
import json
import asyncpg
import asyncio
from typing import Optional
from a2a.server.tasks import TaskStore
from a2a.types import Task

class PostgresTaskStore(TaskStore):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
        self._lock = asyncio.Lock()

    async def connect(self):
        if self.pool:
            return
            
        async with self._lock:
            if self.pool:
                return

        retries = 5
        for i in range(retries):
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                await self._init_db()
                return
            except Exception as e:
                if i == retries - 1:
                    raise e
                # logging.warning(f"Database connection failed. Retrying in 2s... ({i+1}/{retries})")
                await asyncio.sleep(2)

    async def _init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    stream_id TEXT,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

    async def save_task(self, task: Task):
        if not self.pool:
            await self.connect()
        
        # Serialize task data
        # Check if task has model_dump_json (Pydantic v2) or json (Pydantic v1)
        if hasattr(task, 'model_dump_json'):
            task_data = task.model_dump_json()
        else:
            task_data = task.json()
            
        stream_id = getattr(task, 'stream_id', None)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, stream_id, data)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (id) DO UPDATE SET data = $3
            """, task.id, stream_id, task_data)

    async def get_task(self, task_id: str) -> Optional[Task]:
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM tasks WHERE id = $1", task_id)
            if row:
                # Deserialize task data
                if hasattr(Task, 'model_validate_json'):
                    return Task.model_validate_json(row['data'])
                else:
                    return Task.parse_raw(row['data'])
            return None

    # Implement abstract methods required by TaskStore
    # Note: A2A SDK may pass additional arguments like call_context
    async def get(self, task_id: str, *args, **kwargs) -> Optional[Task]:
        return await self.get_task(task_id)

    # Note: A2A SDK may pass additional arguments like call_context
    async def save(self, task: Task, *args, **kwargs) -> None:
        await self.save_task(task)

    # Note: A2A SDK may pass additional arguments like call_context
    async def delete(self, task_id: str, *args, **kwargs) -> None:
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
