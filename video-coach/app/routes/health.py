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
            "ai_models": {
                "face_detection": "unhealthy",
                "pose_estimation": "unhealthy",
                "gesture_recognition": "unhealthy"
            }
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

    # Check AI models
    try:
        import mediapipe as mp
        face_mesh = mp.solutions.face_mesh.FaceMesh()
        health_status["dependencies"]["ai_models"]["face_detection"] = "healthy"
        
        pose = mp.solutions.pose.Pose()
        health_status["dependencies"]["ai_models"]["pose_estimation"] = "healthy"
        
        hands = mp.solutions.hands.Hands()
        health_status["dependencies"]["ai_models"]["gesture_recognition"] = "healthy"
        
        # Cleanup
        face_mesh.close()
        pose.close()
        hands.close()
        
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["ai_models"]["error"] = str(e)

    # Check memory usage
    try:
        import psutil
        memory = psutil.Process().memory_info()
        health_status["resources"] = {
            "memory_used_mb": memory.rss / 1024 / 1024,
            "memory_percent": psutil.Process().memory_percent()
        }
    except Exception as e:
        health_status["resources"] = {"error": str(e)}

    return health_status
