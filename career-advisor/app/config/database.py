from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from pymilvus import connections
from loguru import logger

from app.config.settings import settings

# PostgreSQL
async_engine = create_async_engine(
    settings.get_postgres_uri,
    echo=False,
    future=True,
    poolclass=NullPool,
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Redis
redis_client = redis.Redis.from_url(
    settings.get_redis_uri,
    encoding="utf-8",
    decode_responses=True
)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Dependency for getting Redis client"""
    try:
        yield redis_client
    finally:
        await redis_client.close()

# Milvus
def init_milvus():
    """Initialize Milvus connection"""
    try:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        logger.info("Successfully connected to Milvus")
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {str(e)}")
        raise

def close_milvus():
    """Close Milvus connection"""
    try:
        connections.disconnect("default")
        logger.info("Successfully disconnected from Milvus")
    except Exception as e:
        logger.error(f"Error disconnecting from Milvus: {str(e)}")

async def init_db():
    """Initialize all database connections"""
    try:
        # Test PostgreSQL connection
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        logger.info("Successfully connected to PostgreSQL")

        # Test Redis connection
        await redis_client.ping()
        logger.info("Successfully connected to Redis")

        # Initialize Milvus
        init_milvus()

    except Exception as e:
        logger.error(f"Error initializing database connections: {str(e)}")
        raise

async def close_db():
    """Close all database connections"""
    try:
        # Close Redis connection
        await redis_client.close()
        logger.info("Successfully closed Redis connection")

        # Close Milvus connection
        close_milvus()

        # Close PostgreSQL connection pool
        await async_engine.dispose()
        logger.info("Successfully closed PostgreSQL connections")

    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise
