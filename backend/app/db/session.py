from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    from app.models import get_document_models
    await init_beanie(
        database=_client[settings.MONGODB_DB_NAME],
        document_models=get_document_models(),
    )


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
