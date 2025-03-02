from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.routes import job, health
from app.services.job import JobService

# Create FastAPI app
app = FastAPI(
    title="Job Matching Service",
    description="AI-powered job matching and career recommendation service",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request timing and status"""
    start_time = time.time()
    response = await call_next(request)
    end_time = time.time()
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Duration: {(end_time - start_time):.3f}s"
    )
    return response

# Include routers
app.include_router(job.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(health.router, prefix="/health", tags=["health"])

# Create scheduler for background tasks
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        logger.info("Starting Job Matching Service...")
        
        # Initialize database connections
        from app.config.database import init_db
        await init_db()
        logger.info("Database connections initialized")

        # Initialize job service
        job_service = JobService()
        
        # Schedule job refresh tasks
        if settings.ENABLE_REAL_TIME_UPDATES:
            # Refresh job listings every hour
            scheduler.add_job(
                job_service.refresh_job_listings,
                "interval",
                hours=1,
                id="refresh_jobs",
                next_run_time=None
            )

            # Update market trends daily
            scheduler.add_job(
                job_service.update_market_trends,
                "cron",
                hour=0,  # At midnight
                id="update_trends",
                next_run_time=None
            )

            # Start scheduler
            scheduler.start()
            logger.info("Background tasks scheduled")

        # Initialize Milvus collections
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            
            # Create collection if not exists
            if not Collection(settings.MILVUS_COLLECTION).exists():
                dim = settings.EMBEDDING_DIM
                fields = [
                    FieldSchema(name="id", dtype=str, is_primary=True),
                    FieldSchema(name="embedding", dtype=list, dim=dim),
                    FieldSchema(name="job_id", dtype=str),
                    FieldSchema(name="created_at", dtype=int)
                ]
                schema = CollectionSchema(fields)
                Collection(settings.MILVUS_COLLECTION, schema)
                logger.info("Milvus collection created")
        except Exception as e:
            logger.error(f"Error initializing Milvus: {str(e)}")

        # Initialize AI models
        if settings.ENABLE_SMART_MATCHING:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
                if settings.USE_GPU:
                    model.to('cuda')
                logger.info("AI models loaded")
            except Exception as e:
                logger.error(f"Error loading AI models: {str(e)}")

        # Monitor system resources
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

        logger.info("Job Matching Service started successfully")

    except Exception as e:
        logger.error(f"Error starting service: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down Job Matching Service...")
        
        # Stop scheduler
        scheduler.shutdown()
        logger.info("Background tasks stopped")
        
        # Close database connections
        from app.config.database import close_db
        await close_db()
        logger.info("Database connections closed")

        # Close Milvus connection
        try:
            from pymilvus import connections
            connections.disconnect("default")
            logger.info("Milvus connection closed")
        except Exception as e:
            logger.warning(f"Error closing Milvus connection: {str(e)}")

        # Free GPU memory if used
        if settings.USE_GPU:
            try:
                import torch
                torch.cuda.empty_cache()
                logger.info("GPU memory cleared")
            except Exception as e:
                logger.warning(f"Error clearing GPU memory: {str(e)}")

        logger.info("Job Matching Service shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Job Matching Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "job_search": "/api/jobs/search",
            "recommendations": "/api/jobs/recommendations/{user_id}",
            "skill_gaps": "/api/jobs/skill-gaps/{job_id}/{user_id}",
            "market_analysis": "/api/jobs/market-analysis",
            "health": "/health"
        }
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    
    # Log additional request details for debugging
    logger.error(f"Request details:")
    logger.error(f"  URL: {request.url}")
    logger.error(f"  Method: {request.method}")
    logger.error(f"  Headers: {request.headers}")
    
    try:
        body = await request.json()
        logger.error(f"  Body: {body}")
    except:
        pass
    
    return {
        "status": "error",
        "message": "An unexpected error occurred",
        "detail": str(exc),
        "type": exc.__class__.__name__
    }
