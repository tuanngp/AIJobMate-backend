from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config.settings import settings
from app.routes import interview, health

# Create FastAPI app
app = FastAPI(
    title="Interview Practice Service",
    description="AI-powered interview practice and analysis service",
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

# Include routers
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
app.include_router(health.router, prefix="/health", tags=["health"])

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    try:
        logger.info("Starting Interview Practice Service...")
        
        # Initialize database connections
        from app.config.database import init_db
        await init_db()
        logger.info("Database connections initialized")

        # Initialize AI models (preload if needed)
        from app.services.ai import AIService
        ai_service = AIService()
        logger.info("AI models initialized")

        # Create upload directory if it doesn't exist
        import os
        os.makedirs("/tmp/interview-uploads", exist_ok=True)
        logger.info("Upload directory created")

        logger.info("Interview Practice Service started successfully")

    except Exception as e:
        logger.error(f"Error starting service: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down Interview Practice Service...")
        
        # Close database connections
        from app.config.database import close_db
        await close_db()
        logger.info("Database connections closed")

        # Cleanup temporary files
        import shutil
        try:
            shutil.rmtree("/tmp/interview-uploads")
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")

        logger.info("Interview Practice Service shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Interview Practice Service",
        "version": "1.0.0",
        "status": "running"
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "status": "error",
        "message": "An unexpected error occurred",
        "detail": str(exc)
    }
