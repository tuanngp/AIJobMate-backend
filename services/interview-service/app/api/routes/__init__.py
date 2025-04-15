from fastapi import APIRouter

from app.api.routes import interviews

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(interviews.router, prefix="/interviews", tags=["interviews"]) 