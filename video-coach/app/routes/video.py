from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from sqlalchemy import select

from app.config.database import get_db, get_redis
from app.models.video import VideoSession
from app.schemas.video import (
    VideoSessionCreate,
    VideoSession as VideoSessionSchema,
    VideoAnalysisResponse,
    VideoSessionSummary,
    VideoProgress,
    BatchProcessingResponse,
    VideoUploadResponse,
    Resolution
)
from app.services.video import VideoService
from app.services.ai import AIService

router = APIRouter()

@router.post("/sessions/", response_model=VideoSessionSchema)
async def create_video_session(
    session_data: VideoSessionCreate,
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(VideoService)
) -> VideoSession:
    """Create a new video interview session"""
    return await video_service.create_session(db, session_data)

@router.post("/sessions/{session_id}/upload", response_model=VideoUploadResponse)
async def upload_interview_video(
    session_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    video_service: VideoService = Depends(VideoService)
) -> VideoUploadResponse:
    """Upload video recording for interview session"""
    # Upload video
    video_url, thumbnail_url, duration, resolution = await video_service.upload_video(
        file,
        session_id,
        db
    )

    # Start background processing
    if background_tasks:
        background_tasks.add_task(
            video_service.process_video,
            session_id=session_id,
            db=db,
            redis=redis
        )

    return VideoUploadResponse(
        session_id=session_id,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        duration=duration,
        file_format=file.filename.split('.')[-1].lower(),
        resolution=resolution
    )

@router.get("/sessions/{session_id}/analysis", response_model=VideoAnalysisResponse)
async def get_video_analysis(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    video_service: VideoService = Depends(VideoService)
) -> VideoAnalysisResponse:
    """Get analysis results for a video session"""
    # Try cache first
    cache_key = f"video_analysis:{session_id}"
    cached = await redis.get(cache_key)
    if cached:
        return VideoAnalysisResponse.model_validate_json(cached)

    # Get from database
    stmt = select(VideoSession).where(VideoSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_processed:
        raise HTTPException(
            status_code=202,
            detail="Video analysis is still processing"
        )

    if session.processing_error:
        raise HTTPException(
            status_code=500,
            detail=session.processing_error
        )

    # Process video if not cached
    return await video_service.process_video(session_id, db, redis)

@router.get("/users/{user_id}/sessions", response_model=List[VideoSessionSummary])
async def get_user_sessions(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[VideoSession]:
    """Get all video sessions for a user"""
    stmt = select(VideoSession).where(
        VideoSession.user_id == user_id
    ).order_by(VideoSession.created_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")

    return [
        VideoSessionSummary(
            id=session.id,
            interview_type=session.interview_type,
            job_role=session.job_role,
            duration=session.duration,
            overall_score=session.performance_metrics.get("overall_score", 0) if session.performance_metrics else 0,
            key_strengths=session.strengths[:3] if session.strengths else [],
            main_improvements=list(session.improvement_areas.keys())[:3] if session.improvement_areas else [],
            thumbnail_url=session.thumbnail_url,
            created_at=session.created_at,
            status="processed" if session.is_processed else "processing"
        )
        for session in sessions
    ]

@router.get("/users/{user_id}/progress", response_model=VideoProgress)
async def get_user_progress(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> VideoProgress:
    """Get user's video interview practice progress"""
    # Get all completed sessions
    stmt = select(VideoSession).where(
        VideoSession.user_id == user_id,
        VideoSession.is_processed == True
    ).order_by(VideoSession.created_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No completed sessions found")

    # Calculate statistics
    total_sessions = len(sessions)
    average_scores = {
        "confidence": sum(s.performance_metrics.get("confidence_score", 0) for s in sessions) / total_sessions,
        "engagement": sum(s.performance_metrics.get("engagement_score", 0) for s in sessions) / total_sessions,
        "professionalism": sum(s.performance_metrics.get("professionalism_score", 0) for s in sessions) / total_sessions,
        "overall": sum(s.performance_metrics.get("overall_score", 0) for s in sessions) / total_sessions
    }

    # Collect strengths and improvements
    all_strengths = []
    all_improvements = []
    score_history = []
    
    for session in sessions:
        if session.strengths:
            all_strengths.extend(session.strengths)
        if session.improvement_areas:
            all_improvements.extend(session.improvement_areas.keys())
        score_history.append({
            "date": session.created_at,
            "score": session.performance_metrics.get("overall_score", 0)
        })

    # Get most common items
    from collections import Counter
    top_strengths = [item[0] for item in Counter(all_strengths).most_common(3)]
    common_improvements = [item[0] for item in Counter(all_improvements).most_common(3)]

    # Calculate improvement trends
    improvement_trends = {}
    for area in set(all_improvements):
        scores = []
        for session in sessions:
            if area in session.improvement_areas:
                scores.append(session.improvement_areas[area].get("score", 0))
        if scores:
            improvement_trends[area] = scores

    return VideoProgress(
        total_sessions=total_sessions,
        average_scores=average_scores,
        top_strengths=top_strengths,
        common_improvements=common_improvements,
        score_history=score_history,
        practice_recommendations=[
            f"Focus on improving {area}" for area in common_improvements[:3]
        ],
        improvement_trends=improvement_trends
    )

@router.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_videos(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    video_service: VideoService = Depends(VideoService)
) -> BatchProcessingResponse:
    """Process multiple video recordings in batch"""
    processed_count = 0
    failed_count = 0
    errors = []

    for file in files:
        try:
            # Create session
            session = await video_service.create_session(
                db,
                VideoSessionCreate(
                    interview_type="batch",
                    job_role="batch_processing"
                )
            )

            # Upload video
            await video_service.upload_video(file, session.id, db)

            # Start processing
            if background_tasks:
                background_tasks.add_task(
                    video_service.process_video,
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
async def delete_video_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Delete a video session and its associated data"""
    stmt = select(VideoSession).where(VideoSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete video and thumbnail from S3 if they exist
    import boto3
    s3_client = boto3.client('s3')
    
    if session.video_url:
        try:
            s3_key = session.video_url.split('?')[0].split(settings.AWS_S3_BUCKET + '/')[-1]
            s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key
            )
        except Exception as e:
            pass  # Continue even if video deletion fails

    if session.thumbnail_url:
        try:
            thumb_key = session.thumbnail_url.split('?')[0].split(settings.AWS_S3_BUCKET + '/')[-1]
            s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=thumb_key
            )
        except Exception as e:
            pass

    # Delete from database
    await db.delete(session)
    await db.commit()

    # Clear cache
    cache_key = f"video_analysis:{session_id}"
    await redis.delete(cache_key)

    return {"status": "success", "message": "Video session deleted successfully"}
