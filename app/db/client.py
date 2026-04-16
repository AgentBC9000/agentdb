import databases
from supabase import create_client, Client
from app.core.config import settings

database = databases.Database(settings.DATABASE_URL)

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_db():
    async with database.transaction():
        yield database


async def connect_db():
    await database.connect()


async def disconnect_db():
    await database.disconnect()
