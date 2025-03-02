from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.config.database import get_db, get_redis

router = APIRouter()

@router.get("/")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> dict:
    """
    Check the health of the service and its dependencies
    """
    health_status = {
        "service": "healthy",
        "dependencies": {
            "database": "unhealthy",
            "redis": "unhealthy",
        }
    }

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["database"] = str(e)

    # Check Redis
    try:
        await redis.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["redis"] = str(e)

    return health_status
