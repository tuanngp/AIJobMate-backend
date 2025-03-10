from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"/{settings.API_VERSION}/openapi.json",
    docs_url=f"/{settings.API_VERSION}/docs",
    redoc_url=f"/{settings.API_VERSION}/redoc",
)

# Thêm middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm middleware TrustedHost
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Trong môi trường production nên giới hạn các host được phép
)

# Thêm router API
app.include_router(api_router, prefix=f"/{settings.API_VERSION}")

@app.get("/")
async def root():
    """
    Root endpoint trả về thông tin cơ bản của service
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint để kiểm tra trạng thái service
    """
    return {
        "status": "healthy",
    } 