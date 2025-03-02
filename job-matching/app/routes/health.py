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
            "milvus": "unhealthy",
            "search_engine": "unhealthy",
            "ai_models": {
                "embeddings": "unhealthy",
                "skill_extractor": "unhealthy",
                "job_classifier": "unhealthy"
            }
        },
        "resources": {},
        "job_stats": {
            "total_jobs": 0,
            "active_jobs": 0,
            "jobs_updated_24h": 0
        }
    }

    # Check PostgreSQL
    try:
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(*) FILTER (WHERE is_active = true) as active_jobs,
                COUNT(*) FILTER (WHERE updated_at >= NOW() - INTERVAL '24 hours') as recent_jobs
            FROM jobs
        """))
        stats = result.mappings().first()
        
        health_status["dependencies"]["database"] = "healthy"
        health_status["job_stats"].update({
            "total_jobs": stats["total_jobs"],
            "active_jobs": stats["active_jobs"],
            "jobs_updated_24h": stats["recent_jobs"]
        })
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

    # Check Milvus
    try:
        from pymilvus import connections, Collection
        connections.connect(
            alias="default",
            host="localhost",
            port=19530
        )
        collection = Collection("job_embeddings")
        collection.flush()
        health_status["dependencies"]["milvus"] = "healthy"
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["milvus"] = str(e)

    # Check AI models
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        health_status["dependencies"]["ai_models"]["embeddings"] = "healthy"
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["ai_models"]["embeddings"] = str(e)

    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        health_status["dependencies"]["ai_models"]["skill_extractor"] = "healthy"
    except Exception as e:
        health_status["service"] = "unhealthy"
        health_status["dependencies"]["ai_models"]["skill_extractor"] = str(e)

    # Check system resources
    try:
        import psutil
        memory = psutil.Process().memory_info()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage('/')
        
        health_status["resources"] = {
            "memory_used_mb": memory.rss / 1024 / 1024,
            "memory_percent": psutil.Process().memory_percent(),
            "cpu_percent": cpu_percent,
            "disk_used_percent": disk_usage.percent
        }
    except Exception as e:
        health_status["resources"] = {"error": str(e)}

    return health_status
