from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.routes import router as api_router
from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
from app.services.connection_manager import ConnectionManager
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tạo database tables
Base.metadata.create_all(bind=engine)

# Tạo instance của ConnectionManager
connection_manager = ConnectionManager()

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo các kết nối, cơ sở dữ liệu, cache, v.v.
    logger.info("Starting up the application...")
    logger.info(f"Auth service URL: {settings.AUTH_SERVICE_URL}")
    logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
    
    yield
    
    # Dọn dẹp tài nguyên khi shutdown
    logger.info("Shutting down the application...")
    await connection_manager.close_all()


# Tạo ứng dụng FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Interview Service - Hệ thống hỗ trợ luyện tập phỏng vấn",
    version="1.0.0",
    lifespan=lifespan,
)

# Thiết lập CORS
origins = [origin for origin in settings.CORS_ORIGINS] if isinstance(settings.CORS_ORIGINS, list) else ["*"]
logger.info(f"Setting up CORS with origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm endpoint /metrics cho Prometheus monitoring
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Đăng ký các router API
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}

# Test auth endpoint
@app.get("/test-auth")
async def test_auth():
    return {
        "auth_service_url": settings.AUTH_SERVICE_URL,
        "auth_service_api_version": settings.AUTH_SERVICE_API_VERSION,
        "full_auth_url": f"{settings.AUTH_SERVICE_URL}/auth/verify"
    }

# Tùy chỉnh schema OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=f"{settings.PROJECT_NAME} API",
        version=settings.VERSION,
        description="API của AI Interview Service",
        routes=app.routes,
    )
    
    # Tùy chỉnh OpenAPI schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)