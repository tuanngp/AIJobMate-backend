from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.database import get_db, get_redis
from app.models.data import (
    DataSource,
    CollectionJob,
    Pipeline,
    PipelineRun,
    Monitor,
    Alert
)
from app.schemas.data import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSource as DataSourceSchema,
    CollectionResponse,
    ProcessingResponse,
    MonitoringResponse,
    SystemMetrics,
    DataQualityMetrics,
    PipelineConfig,
    PipelineRun as PipelineRunSchema
)
from app.services.collector import DataCollectionService
from app.services.pipeline import DataPipeline

router = APIRouter()

@router.post("/sources", response_model=DataSourceSchema)
async def create_data_source(
    source_data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> DataSourceSchema:
    """Create a new data source"""
    return await collector.create_data_source(source_data, db)

@router.get("/sources", response_model=List[DataSourceSchema])
async def list_data_sources(
    active_only: bool = True,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[DataSourceSchema]:
    """List all data sources"""
    return await DataCollectionService.list_data_sources(
        active_only,
        type,
        skip,
        limit,
        db
    )

@router.get("/sources/{source_id}", response_model=DataSourceSchema)
async def get_data_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> DataSourceSchema:
    """Get data source details"""
    source = await DataCollectionService.get_data_source(source_id, db)
    if not source:
        raise HTTPException(
            status_code=404,
            detail="Data source not found"
        )
    return source

@router.patch("/sources/{source_id}", response_model=DataSourceSchema)
async def update_data_source(
    source_id: UUID,
    update_data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> DataSourceSchema:
    """Update data source"""
    return await collector.update_data_source(source_id, update_data, db)

@router.post("/sources/{source_id}/collect", response_model=CollectionResponse)
async def start_collection(
    source_id: UUID,
    params: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> CollectionResponse:
    """Start data collection job"""
    job = await collector.create_collection_job(source_id, params, db)
    return CollectionResponse(
        job_id=job.id,
        status=job.status,
        message="Collection job started"
    )

@router.get("/jobs/{job_id}/status", response_model=CollectionResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> CollectionResponse:
    """Get collection job status"""
    return await collector.get_collection_status(job_id, db)

@router.post("/pipelines", response_model=Pipeline)
async def create_pipeline(
    config: PipelineConfig,
    db: AsyncSession = Depends(get_db),
    pipeline_service: DataPipeline = Depends(DataPipeline)
) -> Pipeline:
    """Create a new data pipeline"""
    return await pipeline_service.create_pipeline(config, db)

@router.post("/pipelines/{pipeline_id}/run", response_model=PipelineRunSchema)
async def run_pipeline(
    pipeline_id: UUID,
    params: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    pipeline_service: DataPipeline = Depends(DataPipeline)
) -> PipelineRunSchema:
    """Run a data pipeline"""
    return await pipeline_service.run_pipeline(pipeline_id, params, db)

@router.get("/pipelines/{pipeline_id}/runs", response_model=List[PipelineRunSchema])
async def list_pipeline_runs(
    pipeline_id: UUID,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[PipelineRunSchema]:
    """List pipeline runs"""
    return await DataPipeline.list_pipeline_runs(
        pipeline_id,
        status,
        skip,
        limit,
        db
    )

@router.get("/runs/{run_id}/status", response_model=ProcessingResponse)
async def get_pipeline_status(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    pipeline_service: DataPipeline = Depends(DataPipeline)
) -> ProcessingResponse:
    """Get pipeline run status"""
    return await pipeline_service.get_run_status(run_id, db)

@router.post("/monitors", response_model=Monitor)
async def create_monitor(
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> Monitor:
    """Create new data quality monitor"""
    return await collector.create_monitor(config, db)

@router.get("/monitors/{monitor_id}/status", response_model=MonitoringResponse)
async def get_monitor_status(
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> MonitoringResponse:
    """Get monitor status"""
    return await collector.get_monitor_status(monitor_id, db)

@router.get("/alerts", response_model=List[Alert])
async def list_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[Alert]:
    """List alerts"""
    return await DataCollectionService.list_alerts(
        severity,
        status,
        start_date,
        end_date,
        skip,
        limit,
        db
    )

@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: UUID,
    status: str,
    resolution: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
):
    """Update alert status"""
    await collector.update_alert(alert_id, status, resolution, db)
    return {"status": "success"}

@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
    collector: DataCollectionService = Depends(DataCollectionService)
) -> SystemMetrics:
    """Get system-wide metrics"""
    return await collector.get_system_metrics(db)

@router.get("/metrics/quality", response_model=DataQualityMetrics)
async def get_quality_metrics(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    pipeline_service: DataPipeline = Depends(DataPipeline)
) -> DataQualityMetrics:
    """Get data quality metrics"""
    return await pipeline_service._calculate_quality_metrics(dataset_id)

@router.get("/health")
async def get_health_status(
    redis: Redis = Depends(get_redis),
    collector: DataCollectionService = Depends(DataCollectionService)
):
    """Get service health status"""
    return {
        "service": "data-collection",
        "status": "healthy",
        "active_jobs": len(collector.active_jobs),
        "redis": await redis.ping()
    }

@router.post("/refresh")
async def refresh_data(
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    collector: DataCollectionService = Depends(DataCollectionService)
):
    """Refresh all data sources"""
    task_id = str(UUID())
    
    # Set initial task status
    await redis.set(
        f"refresh_task:{task_id}",
        "running",
        ex=3600  # 1 hour expiry
    )
    
    # Start refresh in background
    background_tasks.add_task(
        collector.refresh_all_sources,
        force=force,
        db=db,
        task_id=task_id
    )
    
    return {
        "task_id": task_id,
        "status": "refresh started"
    }

@router.get("/refresh/{task_id}")
async def get_refresh_status(
    task_id: UUID,
    redis: Redis = Depends(get_redis)
):
    """Get data refresh status"""
    status = await redis.get(f"refresh_task:{task_id}")
    if not status:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return {
        "task_id": task_id,
        "status": status.decode()
    }

@router.post("/validate")
async def validate_data(
    dataset_id: UUID,
    rules: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    pipeline_service: DataPipeline = Depends(DataPipeline)
):
    """Validate dataset against rules"""
    validation_results = await pipeline_service._validate_data(
        rules,
        {"dataset_id": dataset_id},
        db
    )
    return validation_results
