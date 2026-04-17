import databases
from supabase import create_client, Client
from app.core.config import settings

# Async DB for FastAPI (queries)
# statement_cache_size=0 required for Supabase PgBouncer (transaction pooling mode)
database = databases.Database(settings.DATABASE_URL, statement_cache_size=0)

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
