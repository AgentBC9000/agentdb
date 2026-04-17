import re
import asyncpg
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

_pool: Optional[asyncpg.Pool] = None


def _clean_db_url(url: str) -> str:
    """Convert postgresql+asyncpg:// to postgresql:// and strip query params."""
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in url:
        url = url.split("?")[0]
    return url


class AsyncDB:
    """
    Thin asyncpg wrapper matching the databases library API.
    Translates :param-style queries to asyncpg $1-style so no
    endpoint/service code needs to change.
    """

    def _convert(self, query: str, values: dict) -> tuple[str, list]:
        params = []
        def replace(m):
            params.append(values[m.group(1)])
            return f"${len(params)}"
        # (?<!:) negative lookbehind — skip :: PostgreSQL type casts
        return re.sub(r"(?<!:):(\w+)", replace, query), params

    async def fetch_one(self, query: str, values: dict = None):
        q, p = self._convert(query, values or {})
        async with _pool.acquire() as conn:
            return await conn.fetchrow(q, *p)

    async def fetch_all(self, query: str, values: dict = None):
        q, p = self._convert(query, values or {})
        async with _pool.acquire() as conn:
            return await conn.fetch(q, *p)

    async def execute(self, query: str, values: dict = None):
        q, p = self._convert(query, values or {})
        async with _pool.acquire() as conn:
            await conn.execute(q, *p)


database = AsyncDB()

# Supabase client (auth, storage, admin ops)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_db():
    """FastAPI dependency — yields database interface."""
    yield database


async def connect_db():
    global _pool
    dsn = _clean_db_url(settings.DATABASE_URL)
    _pool = await asyncpg.create_pool(
        dsn,
        statement_cache_size=0,   # Required for Supabase PgBouncer transaction mode
        min_size=2,
        max_size=10,
    )


async def disconnect_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
