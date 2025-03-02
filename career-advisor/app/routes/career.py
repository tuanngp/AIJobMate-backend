from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.config.database import get_db, get_redis
from app.models.career import User, CareerAdvice
from app.schemas.career import (
    UserCreate,
    User as UserSchema,
    CareerAdviceCreate,
    CareerAdvice as CareerAdviceSchema,
    CVUpload,
    CareerAnalysisResponse,
    CareerAdviceRequest,
    CareerAdviceResponse,
    JobPreferences,
    BatchProcessingResponse
)
from app.services.career import CareerService
from app.services.ai import AIService

router = APIRouter()

@router.post("/users/", response_model=UserSchema)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Create a new user"""
    db_user = User(email=user.email, profile=user.profile)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/upload-cv/", response_model=CareerAdviceSchema)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: UUID = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    career_service: CareerService = Depends(CareerService),
) -> CareerAdvice:
    """Upload and analyze a CV"""
    # Read file content
    content = await file.read()
    
    # Create career advice entry
    career_advice = await career_service.create_cv_analysis(
        db=db,
        user_id=user_id,
        file_content=content,
        file_name=file.filename
    )

    # Start background processing
    background_tasks.add_task(
        career_service.process_cv_analysis,
        career_advice_id=career_advice.id,
        db=db,
        redis=redis
    )

    return career_advice

@router.get("/analysis/{career_advice_id}", response_model=CareerAnalysisResponse)
async def get_cv_analysis(
    career_advice_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    career_service: CareerService = Depends(CareerService)
) -> CareerAnalysisResponse:
    """Get CV analysis results"""
    # Try to get from cache first
    cache_key = f"cv_analysis:{career_advice_id}"
    cached_result = await redis.get(cache_key)
    if cached_result:
        return CareerAnalysisResponse.model_validate_json(cached_result)

    # Get from database
    career_advice = await career_service.get_cv_analysis(db, career_advice_id)
    if not career_advice:
        raise HTTPException(status_code=404, detail="CV analysis not found")

    if not career_advice.is_processed:
        raise HTTPException(status_code=202, detail="CV analysis is still processing")

    if career_advice.processing_error:
        raise HTTPException(status_code=500, detail=career_advice.processing_error)

    # Create response
    response = CareerAnalysisResponse(
        skills_analysis={
            "identified_skills": career_advice.skills,
            "strengths": career_advice.strengths,
            "weaknesses": career_advice.weaknesses
        },
        career_suggestions=career_advice.career_paths,
        improvement_recommendations=career_advice.improvement_areas
    )

    # Cache the result
    await redis.set(
        cache_key,
        response.model_dump_json(),
        ex=3600  # 1 hour
    )

    return response

@router.post("/advice/", response_model=CareerAdviceResponse)
async def get_career_advice(
    request: CareerAdviceRequest,
    career_advice_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    ai_service: AIService = Depends(AIService),
    career_service: CareerService = Depends(CareerService)
) -> CareerAdviceResponse:
    """Get personalized career advice based on CV analysis and preferences"""
    # Get CV analysis
    career_advice = await career_service.get_cv_analysis(db, career_advice_id)
    if not career_advice:
        raise HTTPException(status_code=404, detail="CV analysis not found")

    if not career_advice.is_processed:
        raise HTTPException(status_code=202, detail="CV analysis is still processing")

    # Cache key for advice
    cache_key = f"career_advice:{career_advice_id}:{hash(request.model_dump_json())}"
    cached_result = await redis.get(cache_key)
    if cached_result:
        return CareerAdviceResponse.model_validate_json(cached_result)

    # Generate advice using AI
    response = await ai_service.generate_career_advice(
        cv_analysis=career_advice,
        preferences=request.preferences,
        additional_context=request.additional_context
    )

    # Cache the result
    await redis.set(
        cache_key,
        response.model_dump_json(),
        ex=3600  # 1 hour
    )

    # Update advice history
    career_advice.advice_history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "preferences": request.preferences.model_dump(),
        "advice": response.model_dump()
    })
    await db.commit()

    return response

@router.get("/user/{user_id}/history", response_model=List[CareerAdviceSchema])
async def get_user_advice_history(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    career_service: CareerService = Depends(CareerService)
) -> List[CareerAdvice]:
    """Get user's career advice history"""
    history = await career_service.get_user_advice_history(db, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="No advice history found")
    return history

@router.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_cvs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    career_service: CareerService = Depends(CareerService)
) -> BatchProcessingResponse:
    """Process multiple CVs in batch"""
    processed_count = 0
    failed_count = 0
    errors = []

    for file in files:
        try:
            content = await file.read()
            career_advice = await career_service.create_cv_analysis(
                db=db,
                file_content=content,
                file_name=file.filename
            )
            background_tasks.add_task(
                career_service.process_cv_analysis,
                career_advice_id=career_advice.id,
                db=db,
                redis=redis
            )
            processed_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({"file": file.filename, "error": str(e)})

    return BatchProcessingResponse(
        success=failed_count == 0,
        processed_count=processed_count,
        failed_count=failed_count,
        errors=errors
    )

@router.delete("/advice/{career_advice_id}")
async def delete_career_advice(
    career_advice_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    career_service: CareerService = Depends(CareerService)
):
    """Delete a career advice record"""
    deleted = await career_service.delete_cv_analysis(db, career_advice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="CV analysis not found")
    
    # Clear cache
    await redis.delete(f"cv_analysis:{career_advice_id}")
    await redis.delete(f"career_advice:{career_advice_id}:*")
    
    return {"status": "success", "message": "Career advice deleted successfully"}
