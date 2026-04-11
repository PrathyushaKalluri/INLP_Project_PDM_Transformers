from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    global _client
    try:
        if not settings.MONGODB_URL:
            raise RuntimeError(
                "MONGODB_URL is not set. Add your MongoDB Atlas connection string in the Render environment variables."
            )

        if settings.MONGODB_URL.startswith("mongodb://localhost"):
            raise RuntimeError(
                "MONGODB_URL is still pointing to localhost. Replace it with your MongoDB Atlas URI on Render."
            )

        # Create client with a short connection timeout so startup does not block for long.
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        
        from app.models import get_document_models
        await init_beanie(
            database=_client[settings.MONGODB_DB_NAME],
            document_models=get_document_models(),
        )
        print("✓ MongoDB connected successfully")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
