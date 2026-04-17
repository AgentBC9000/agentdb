import databases
from supabase import create_client, Client
from app.core.config import settings

# Async DB for FastAPI (queries)
# statement_cache_size=0 required for Supabase PgBouncer (transaction pooling mode)
_db_url = settings.DATABASE_URL
if "statement_cache_size" not in _db_url:
    _db_url += ("&" if "?" in _db_url else "?") + "statement_cache_size=0"
database = databases.Database(_db_url)

# Supabase client (auth, storage, admin ops)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_db():
    """FastAPI dependency — yields connected async DB."""
    async with database.transaction():
        yield database


async def connect_db():
    await database.connect()


async def disconnect_db():
    await database.disconnect()
