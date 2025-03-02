from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config.settings import settings
from app.routes import career, health

# Create FastAPI app
app = FastAPI(
    title="Career Advisor Service",
    description="AI-powered career advice and CV analysis service",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(career.router, prefix="/api/career", tags=["career"])
app.include_router(health.router, prefix="/health", tags=["health"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Career Advisor Service...")
    # Initialize database connections
    from app.config.database import init_db
    await init_db()

    # Initialize AI models
    from app.services.ai import init_ai_models
    await init_ai_models()

    logger.info("Career Advisor Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Career Advisor Service...")
    # Close any connections
    from app.config.database import close_db
    await close_db()
    logger.info("Career Advisor Service shut down successfully")
