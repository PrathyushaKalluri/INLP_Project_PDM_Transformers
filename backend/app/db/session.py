from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import asyncio

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    global _client
    try:
        # Create client with connection timeout
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
        )
        
        # Test connection with timeout
        await asyncio.wait_for(
            _client.server_info(),
            timeout=5.0
        )
        
        from app.models import get_document_models
        await init_beanie(
            database=_client[settings.MONGODB_DB_NAME],
            document_models=get_document_models(),
        )
        print("✓ MongoDB connected successfully")
    except asyncio.TimeoutError:
        raise RuntimeError(
            "MongoDB connection timeout (5s). "
            "Make sure MongoDB is running on localhost:27017. "
            "Start with: mongosh or MongoDB Compass"
        )
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
