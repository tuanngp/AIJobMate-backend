from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import time

from app.config.settings import settings
from app.routes import video, health

# Create FastAPI app
app = FastAPI(
    title="Video Interview Coach Service",
    description="AI-powered video interview analysis and coaching service",
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
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(health.router, prefix="/health", tags=["health"])

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        logger.info("Starting Video Interview Coach Service...")
        
        # Initialize database connections
        from app.config.database import init_db
        await init_db()
        logger.info("Database connections initialized")

        # Initialize AI models
        from app.services.ai import AIService
        ai_service = AIService()
        logger.info("AI models initialized")

        # Create required directories
        import os
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.FRAMES_DIR, exist_ok=True)
        logger.info("Storage directories created")

        # Check GPU availability
        import torch
        if torch.cuda.is_available() and settings.USE_GPU:
            logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
            torch.cuda.set_device(0)
        else:
            logger.warning("GPU not available, using CPU")

        # Initialize memory monitoring
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

        logger.info("Video Interview Coach Service started successfully")

    except Exception as e:
        logger.error(f"Error starting service: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down Video Interview Coach Service...")
        
        # Close database connections
        from app.config.database import close_db
        await close_db()
        logger.info("Database connections closed")

        # Cleanup temporary files
        import shutil
        try:
            shutil.rmtree(settings.UPLOAD_DIR)
            shutil.rmtree(settings.FRAMES_DIR)
            logger.info("Temporary directories cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up directories: {str(e)}")

        # Free GPU memory if used
        if settings.USE_GPU:
            try:
                import torch
                torch.cuda.empty_cache()
                logger.info("GPU memory cleared")
            except Exception as e:
                logger.warning(f"Error clearing GPU memory: {str(e)}")

        logger.info("Video Interview Coach Service shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Video Interview Coach Service",
        "version": "1.0.0",
        "status": "running",
        "gpu_enabled": settings.USE_GPU
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
