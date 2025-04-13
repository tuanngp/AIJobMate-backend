from fastapi import APIRouter

from app.api.routes import users, cv

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(cv.router, prefix="/cv", tags=["cv"])