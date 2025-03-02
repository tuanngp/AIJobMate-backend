from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.database import get_db, get_redis
from app.models.job import Job, UserSkillProfile, JobMatch
from app.schemas.job import (
    JobCreate,
    JobSearchParams,
    JobSearchResponse,
    RecommendationResponse,
    SkillGapAnalysis,
    MarketAnalysis,
    JobRecommendation
)
from app.services.job import JobService

router = APIRouter()

@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    query: Optional[str] = None,
    location: Optional[str] = None,
    remote_only: bool = False,
    job_types: Optional[List[str]] = Query(None),
    experience_levels: Optional[List[str]] = Query(None),
    industries: Optional[List[str]] = Query(None),
    min_salary: Optional[int] = None,
    posted_within_days: Optional[int] = None,
    skills: Optional[List[str]] = Query(None),
    company_sizes: Optional[List[str]] = Query(None),
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> JobSearchResponse:
    """Search for jobs with various filters"""
    params = JobSearchParams(
        query=query,
        location=location,
        remote_only=remote_only,
        job_types=job_types,
        experience_levels=experience_levels,
        industries=industries,
        min_salary=min_salary,
        posted_within_days=posted_within_days,
        skills=skills,
        company_sizes=company_sizes,
        sort_by=sort_by,
        page=page,
        page_size=page_size
    )
    return await job_service.search_jobs(params, db)

@router.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_job_recommendations(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> RecommendationResponse:
    """Get personalized job recommendations"""
    return await job_service.get_job_recommendations(user_id, db)

@router.get("/skill-gaps/{job_id}/{user_id}", response_model=SkillGapAnalysis)
async def analyze_skill_gaps(
    job_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> SkillGapAnalysis:
    """Analyze skill gaps for a specific job"""
    return await job_service.analyze_skill_gaps(job_id, user_id, db)

@router.get("/market-analysis", response_model=MarketAnalysis)
async def get_market_analysis(
    job_category: str,
    skills: List[str] = Query(...),
    location: str = Query(...),
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> MarketAnalysis:
    """Get market analysis for given job category and skills"""
    return await job_service.get_market_analysis(
        job_category,
        skills,
        location,
        db
    )

@router.post("/jobs", response_model=Job)
async def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> Job:
    """Create a new job posting"""
    job = await job_service.create_job(job_data, db)
    
    # Start background matching task
    if background_tasks:
        background_tasks.add_task(
            job_service.match_with_candidates,
            job.id,
            db
        )
    
    return job

@router.get("/jobs/{job_id}/matches", response_model=List[JobRecommendation])
async def get_job_matches(
    job_id: UUID,
    min_score: float = 0.7,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> List[JobRecommendation]:
    """Get matching candidates for a job"""
    matches = await job_service.get_job_matches(job_id, min_score, limit, db)
    if not matches:
        raise HTTPException(
            status_code=404,
            detail="No matches found for this job"
        )
    return matches

@router.post("/refresh-jobs")
async def refresh_job_listings(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    job_service: JobService = Depends(JobService)
):
    """Refresh job listings from various sources"""
    # Start refresh task in background
    task_id = str(UUID())
    background_tasks.add_task(
        job_service.refresh_job_listings,
        db=db,
        task_id=task_id
    )
    
    # Set initial task status
    await redis.set(
        f"job_refresh_task:{task_id}",
        "running",
        ex=3600  # 1 hour
    )
    
    return {
        "status": "refresh started",
        "task_id": task_id
    }

@router.get("/refresh-status/{task_id}")
async def get_refresh_status(
    task_id: UUID,
    redis: Redis = Depends(get_redis)
):
    """Get status of job refresh task"""
    status = await redis.get(f"job_refresh_task:{task_id}")
    if not status:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return {
        "task_id": task_id,
        "status": status.decode()
    }

@router.get("/jobs/{job_id}/similar", response_model=List[Job])
async def get_similar_jobs(
    job_id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> List[Job]:
    """Get similar jobs based on content and requirements"""
    similar_jobs = await job_service.find_similar_jobs(job_id, limit, db)
    if not similar_jobs:
        raise HTTPException(
            status_code=404,
            detail="No similar jobs found"
        )
    return similar_jobs

@router.post("/jobs/{job_id}/view")
async def track_job_view(
    job_id: UUID,
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
):
    """Track job view for analytics"""
    await job_service.track_job_view(job_id, user_id, db)
    return {"status": "success"}

@router.get("/trending-jobs")
async def get_trending_jobs(
    time_period: str = "week",
    category: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> List[Dict]:
    """Get trending jobs based on views and applications"""
    return await job_service.get_trending_jobs(
        time_period,
        category,
        location,
        limit,
        db
    )

@router.get("/salary-insights")
async def get_salary_insights(
    job_title: str,
    location: Optional[str] = None,
    experience_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> Dict:
    """Get salary insights for job title"""
    return await job_service.get_salary_insights(
        job_title,
        location,
        experience_level,
        db
    )

@router.post("/jobs/{job_id}/apply")
async def apply_for_job(
    job_id: UUID,
    user_id: UUID,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
):
    """Apply for a job"""
    try:
        await job_service.create_job_application(
            job_id,
            user_id,
            db
        )
        
        # Start background task for application processing
        if background_tasks:
            background_tasks.add_task(
                job_service.process_job_application,
                job_id=job_id,
                user_id=user_id,
                db=db
            )
        
        return {"status": "application submitted"}
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.get("/jobs/stats")
async def get_job_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[List[str]] = Query(None),
    locations: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(JobService)
) -> Dict:
    """Get job market statistics"""
    return await job_service.get_job_stats(
        start_date,
        end_date,
        categories,
        locations,
        db
    )
