from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import psutil
import os
from datetime import datetime

from app.config.database import get_db, get_redis
from app.models.data import DataSource, CollectionJob, Pipeline
from app.services.collector import DataCollectionService
from app.services.pipeline import DataPipeline

router = APIRouter()

@router.get("/")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    collector: DataCollectionService = Depends(DataCollectionService),
    pipeline: DataPipeline = Depends(DataPipeline)
) -> dict:
    """
    Comprehensive health check of the Data Collection service
    """
    health_status = {
        "service": "data-collection",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "dependencies": {
            "database": _check_db_status(db),
            "redis": await _check_redis_status(redis),
            "minio": await _check_minio_status(),
            "elasticsearch": await _check_elasticsearch_status()
        },
        "components": {
            "collector": _check_collector_status(collector),
            "pipeline": _check_pipeline_status(pipeline)
        },
        "resources": _check_system_resources(),
        "metrics": await _get_service_metrics(db)
    }

    # Determine overall status
    dependency_status = all(
        status["status"] == "healthy"
        for status in health_status["dependencies"].values()
    )
    component_status = all(
        status["status"] == "healthy"
        for status in health_status["components"].values()
    )
    resource_status = all(
        usage < 90 for usage in health_status["resources"].values()
    )

    if not all([dependency_status, component_status, resource_status]):
        health_status["status"] = "unhealthy"

    return health_status

async def _check_db_status(db: AsyncSession) -> dict:
    """Check database connection and status"""
    try:
        # Check connection
        result = await db.execute(text("SELECT 1"))
        if result.scalar() != 1:
            raise Exception("Database check failed")

        # Get database metrics
        metrics = await db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM data_sources) as sources_count,
                (SELECT COUNT(*) FROM collection_jobs) as jobs_count,
                (SELECT COUNT(*) FROM pipelines) as pipelines_count,
                pg_database_size(current_database()) as db_size
        """))
        metrics = metrics.mappings().first()

        return {
            "status": "healthy",
            "latency": 0.1,  # TODO: Implement actual latency check
            "metrics": metrics
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _check_redis_status(redis: Redis) -> dict:
    """Check Redis connection and status"""
    try:
        # Check connection
        await redis.ping()

        # Get Redis info
        info = await redis.info()
        return {
            "status": "healthy",
            "version": info["redis_version"],
            "used_memory": info["used_memory_human"],
            "connected_clients": info["connected_clients"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _check_minio_status() -> dict:
    """Check MinIO connection and status"""
    try:
        from minio import Minio
        from app.config.settings import settings

        client = Minio(
            f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

        # Check if bucket exists and list objects
        if client.bucket_exists(settings.MINIO_BUCKET):
            objects = list(
                client.list_objects(
                    settings.MINIO_BUCKET,
                    recursive=True
                )
            )
            return {
                "status": "healthy",
                "bucket": settings.MINIO_BUCKET,
                "object_count": len(objects)
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Bucket not found"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _check_elasticsearch_status() -> dict:
    """Check Elasticsearch connection and status"""
    try:
        from elasticsearch import AsyncElasticsearch
        from app.config.settings import settings

        es = AsyncElasticsearch(
            [f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
            basic_auth=(
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD
            )
        )

        # Check cluster health
        health = await es.cluster.health()
        return {
            "status": "healthy" if health["status"] in ["green", "yellow"] else "unhealthy",
            "cluster_status": health["status"],
            "nodes": health["number_of_nodes"],
            "active_shards": health["active_shards"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def _check_collector_status(collector: DataCollectionService) -> dict:
    """Check data collector component status"""
    try:
        active_jobs = len(collector.active_jobs)
        overloaded = active_jobs >= collector.max_concurrent_jobs

        return {
            "status": "healthy" if not overloaded else "warning",
            "active_jobs": active_jobs,
            "max_jobs": collector.max_concurrent_jobs,
            "rate_limiters": {
                source: limiter._value
                for source, limiter in collector.rate_limiters.items()
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def _check_pipeline_status(pipeline: DataPipeline) -> dict:
    """Check data pipeline component status"""
    try:
        active_pipelines = len(pipeline.active_pipelines)
        return {
            "status": "healthy",
            "active_pipelines": active_pipelines,
            "registered_tasks": list(pipeline.task_registry.keys())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def _check_system_resources() -> dict:
    """Check system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "memory_available": f"{memory.available / (1024 * 1024 * 1024):.2f}GB",
            "disk_available": f"{disk.free / (1024 * 1024 * 1024):.2f}GB"
        }
    except Exception as e:
        return {
            "error": str(e)
        }

async def _get_service_metrics(db: AsyncSession) -> dict:
    """Get service performance metrics"""
    try:
        # Get recent job metrics
        job_metrics = await db.execute(text("""
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_jobs,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_jobs,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration
            FROM collection_jobs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """))
        job_metrics = job_metrics.mappings().first()

        # Get pipeline metrics
        pipeline_metrics = await db.execute(text("""
            SELECT 
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
                AVG(duration) as avg_duration
            FROM pipeline_runs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """))
        pipeline_metrics = pipeline_metrics.mappings().first()

        # Get data metrics
        data_metrics = await db.execute(text("""
            SELECT 
                COUNT(*) as total_records,
                SUM(file_size) as total_size,
                AVG(completeness) as avg_completeness,
                AVG(accuracy) as avg_accuracy
            FROM data_sets
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """))
        data_metrics = data_metrics.mappings().first()

        return {
            "collection_metrics": job_metrics,
            "pipeline_metrics": pipeline_metrics,
            "data_metrics": data_metrics,
            "collection_rate": job_metrics["total_jobs"] / 24 if job_metrics else 0,
            "success_rate": (
                job_metrics["successful_jobs"] / job_metrics["total_jobs"]
                if job_metrics and job_metrics["total_jobs"] > 0
                else 0
            )
        }
    except Exception as e:
        return {
            "error": str(e)
        }

@router.get("/readiness")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> dict:
    """
    Check if service is ready to handle requests
    """
    status = {
        "ready": True,
        "checks": {
            "database": True,
            "redis": True,
            "storage": True
        }
    }

    try:
        # Check database
        await db.execute(text("SELECT 1"))
    except:
        status["checks"]["database"] = False
        status["ready"] = False

    try:
        # Check Redis
        await redis.ping()
    except:
        status["checks"]["redis"] = False
        status["ready"] = False

    try:
        # Check MinIO
        from minio import Minio
        from app.config.settings import settings
        client = Minio(
            f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        client.bucket_exists(settings.MINIO_BUCKET)
    except:
        status["checks"]["storage"] = False
        status["ready"] = False

    return status

@router.get("/liveness")
async def liveness_check() -> dict:
    """
    Check if service is alive
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
