from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.routes import router as api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager

# Tạo database tables
Base.metadata.create_all(bind=engine)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo các kết nối, cơ sở dữ liệu, cache, v.v.
    print("Starting up the application...")
    
    # Khởi tạo Pinecone vector database (sẽ thực hiện trong services)
    
    yield
    
    # Dọn dẹp tài nguyên khi shutdown
    print("Shutting down the application...")


# Tạo ứng dụng FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Career Advisor API Service - Cung cấp tư vấn nghề nghiệp AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Thiết lập CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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

# Tùy chỉnh schema OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=f"{settings.PROJECT_NAME} API",
        version=settings.VERSION,
        description="API của AI Career Advisor Service",
        routes=app.routes,
    )
    
    # Tùy chỉnh OpenAPI schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 