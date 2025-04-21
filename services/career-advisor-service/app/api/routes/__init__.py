from fastapi import APIRouter

from app.api.routes import cv

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(cv.router, prefix="/cv", tags=["cv"])