from fastapi import APIRouter

from app.api.routes import interviews, practice_sessions

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
router.include_router(practice_sessions.router, prefix="/practice-sessions", tags=["practice_sessions"])