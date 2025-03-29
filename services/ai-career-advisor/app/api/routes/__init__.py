from fastapi import APIRouter

from app.api.routes import auth, career_profiles, career_advisor, users, cv

# Tạo router chính
router = APIRouter()

# Đăng ký các sub-routers
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(career_profiles.router, prefix="/career-profiles", tags=["career profiles"])
router.include_router(career_advisor.router, prefix="/career-advisor", tags=["career advisor"])
router.include_router(cv.router, prefix="/cv", tags=["cv"])