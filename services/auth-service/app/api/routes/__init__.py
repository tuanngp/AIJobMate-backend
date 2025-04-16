from fastapi import APIRouter

from app.api.routes import auth, users

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])