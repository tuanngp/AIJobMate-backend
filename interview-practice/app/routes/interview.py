from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.database import get_db, get_redis
from app.models.interview import InterviewSession
from app.schemas.interview import (
    InterviewSessionCreate,
    InterviewSession as InterviewSessionSchema,
    InterviewAnalysisResponse,
    InterviewSessionSummary,
    InterviewProgress,
    BatchProcessingResponse
)
from app.services.interview import InterviewService
from app.services.ai import AIService

router = APIRouter()

@router.post("/sessions/", response_model=InterviewSessionSchema)
async def create_interview_session(
    session_data: InterviewSessionCreate,
    db: AsyncSession = Depends(get_db),
    interview_service: InterviewService = Depends(InterviewService)
) -> InterviewSession:
    """Create a new interview session"""
    return await interview_service.create_session(db, session_data)

@router.post("/sessions/{session_id}/upload", response_model=InterviewSessionSchema)
async def upload_interview_audio(
    session_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    interview_service: InterviewService = Depends(InterviewService)
) -> InterviewSession:
    """Upload audio recording for an interview session"""
    # Upload audio file
    audio_url, metadata = await interview_service.upload_audio(
        file,
        session_id,
        db
    )

    # Start background processing
    if background_tasks:
        background_tasks.add_task(
            interview_service.process_interview,
            session_id=session_id,
            db=db,
            redis=redis
        )

    # Get updated session
    stmt = select(InterviewSession).where(InterviewSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session

@router.get("/sessions/{session_id}/analysis", response_model=InterviewAnalysisResponse)
async def get_interview_analysis(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    interview_service: InterviewService = Depends(InterviewService)
) -> InterviewAnalysisResponse:
    """Get analysis results for an interview session"""
    return await interview_service.get_session_analysis(session_id, db, redis)

@router.get("/users/{user_id}/sessions", response_model=List[InterviewSessionSummary])
async def get_user_sessions(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    interview_service: InterviewService = Depends(InterviewService)
) -> List[InterviewSession]:
    """Get all interview sessions for a user"""
    return await interview_service.get_user_sessions(user_id, db)

@router.get("/users/{user_id}/progress", response_model=InterviewProgress)
async def get_user_progress(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    interview_service: InterviewService = Depends(InterviewService)
) -> InterviewProgress:
    """Get user's interview practice progress and statistics"""
    # Get all user sessions
    sessions = await interview_service.get_user_sessions(user_id, db)
    
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")

    # Calculate statistics
    total_sessions = len(sessions)
    completed_sessions = [s for s in sessions if s.is_processed and not s.processing_error]
    
    if not completed_sessions:
        raise HTTPException(status_code=404, detail="No completed sessions found")

    # Calculate average score
    average_score = sum(s.performance_metrics["overall_score"] for s in completed_sessions) / len(completed_sessions)

    # Collect strengths and improvements
    all_strengths = []
    all_improvements = []
    score_history = []

    for session in completed_sessions:
        # Add strengths from content analysis
        if "strengths" in session.content_analysis:
            all_strengths.extend(session.content_analysis["strengths"])
        
        # Add areas for improvement
        if session.improvement_areas:
            all_improvements.extend(session.improvement_areas.keys())
        
        # Add score to history
        score_history.append({
            "date": session.created_at,
            "score": session.performance_metrics["overall_score"]
        })

    # Get most common strengths and improvements
    from collections import Counter
    top_strengths = [item[0] for item in Counter(all_strengths).most_common(3)]
    common_improvements = [item[0] for item in Counter(all_improvements).most_common(3)]

    # Generate practice recommendations based on common improvements
    practice_recommendations = [
        f"Focus on improving {area}" for area in common_improvements
    ]

    return InterviewProgress(
        total_sessions=total_sessions,
        average_score=average_score,
        top_strengths=top_strengths,
        common_improvements=common_improvements,
        score_history=score_history,
        practice_recommendations=practice_recommendations
    )

@router.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_interviews(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    interview_service: InterviewService = Depends(InterviewService)
) -> BatchProcessingResponse:
    """Process multiple interview recordings in batch"""
    processed_count = 0
    failed_count = 0
    errors = []

    for file in files:
        try:
            # Create session
            session = await interview_service.create_session(
                db,
                InterviewSessionCreate(
                    interview_type="batch",
                    job_role="batch_processing"
                )
            )

            # Upload audio
            await interview_service.upload_audio(file, session.id, db)

            # Start processing
            if background_tasks:
                background_tasks.add_task(
                    interview_service.process_interview,
                    session_id=session.id,
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

@router.delete("/sessions/{session_id}")
async def delete_interview_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    interview_service: InterviewService = Depends(InterviewService)
):
    """Delete an interview session and its associated data"""
    deleted = await interview_service.delete_session(session_id, db, redis)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session deleted successfully"}
