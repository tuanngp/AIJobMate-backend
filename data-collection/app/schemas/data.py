from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator, ConfigDict

# Base schemas
class DataSourceConfig(BaseModel):
    url: str
    auth_type: str = "none"  # none, basic, oauth, api_key
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    rate_limits: Dict[str, int] = Field(default_factory=dict)

class DataSourceStats(BaseModel):
    total_records: int = 0
    success_rate: float = 0.0
    error_count: int = 0
    avg_response_time: float = 0.0
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None

# Data Source schemas
class DataSourceBase(BaseModel):
    name: str
    type: str
    config: DataSourceConfig
    credentials: Dict[str, Any] = Field(default_factory=dict)

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[DataSourceConfig] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class DataSource(DataSourceBase):
    id: UUID
    is_active: bool
    stats: DataSourceStats
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Collection Job schemas
class JobParams(BaseModel):
    query: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    date_range: Optional[Dict[str, datetime]] = None
    limit: Optional[int] = None
    batch_size: int = 1000

class JobMetrics(BaseModel):
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    processing_time: Optional[float] = None
    avg_batch_time: Optional[float] = None
    validation_score: Optional[float] = None

class CollectionJobBase(BaseModel):
    source_id: UUID
    job_type: str
    params: JobParams

class CollectionJobCreate(CollectionJobBase):
    pass

class CollectionJobUpdate(BaseModel):
    params: Optional[JobParams] = None
    status: Optional[str] = None
    progress: Optional[float] = None

class CollectionJob(CollectionJobBase):
    id: UUID
    status: str
    progress: float = 0.0
    metrics: JobMetrics
    error_details: List[Dict[str, Any]] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Dataset schemas
class DatasetSchema(BaseModel):
    fields: Dict[str, str]
    primary_key: Optional[str] = None
    relationships: Dict[str, Any] = Field(default_factory=dict)

class DatasetStats(BaseModel):
    record_count: int
    file_size: int
    field_statistics: Dict[str, Dict[str, Any]]
    quality_metrics: Dict[str, float]

class DatasetBase(BaseModel):
    name: str
    type: str
    format: str
    schema: DatasetSchema
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    required_fields: List[str] = Field(default_factory=list)

class DatasetCreate(DatasetBase):
    source_id: UUID
    collection_job_id: UUID
    location: str

class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    schema: Optional[DatasetSchema] = None
    validation_rules: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_latest: Optional[bool] = None

class Dataset(DatasetBase):
    id: UUID
    source_id: UUID
    collection_job_id: UUID
    location: str
    status: str
    is_latest: bool
    stats: DatasetStats
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list)
    data_lineage: Dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime
    processed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Pipeline schemas
class TaskConfig(BaseModel):
    name: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    retry_count: int = 3
    timeout: int = 3600

class PipelineConfig(BaseModel):
    schedule: Optional[str] = None  # Cron expression
    tasks: List[TaskConfig]
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    params: Dict[str, Any] = Field(default_factory=dict)

class PipelineStats(BaseModel):
    avg_duration: float = 0.0
    success_rate: float = 0.0
    failure_count: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    config: PipelineConfig

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    description: Optional[str] = None
    config: Optional[PipelineConfig] = None
    is_active: Optional[bool] = None

class Pipeline(PipelineBase):
    id: UUID
    is_active: bool
    stats: PipelineStats
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Pipeline Run schemas
class RunParams(BaseModel):
    trigger_type: str
    params: Dict[str, Any] = Field(default_factory=dict)

class TaskResult(BaseModel):
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None

class PipelineRunBase(BaseModel):
    pipeline_id: UUID
    trigger_type: str
    params: Dict[str, Any] = Field(default_factory=dict)

class PipelineRunCreate(PipelineRunBase):
    pass

class PipelineRunUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    current_task: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

class PipelineRun(PipelineRunBase):
    id: UUID
    status: str
    progress: float = 0.0
    current_task: Optional[str] = None
    task_results: Dict[str, TaskResult] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Monitor schemas
class MonitorConfig(BaseModel):
    metrics: List[str]
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None  # Cron expression
    validation_rules: List[Dict[str, Any]] = Field(default_factory=list)
    alert_rules: List[Dict[str, Any]] = Field(default_factory=list)

class MonitorBase(BaseModel):
    name: str
    type: str
    config: MonitorConfig

class MonitorCreate(MonitorBase):
    pass

class MonitorUpdate(BaseModel):
    config: Optional[MonitorConfig] = None
    is_active: Optional[bool] = None

class Monitor(MonitorBase):
    id: UUID
    is_active: bool
    current_status: str
    latest_results: Dict[str, Any] = Field(default_factory=dict)
    last_check: Optional[datetime] = None
    last_alert: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Alert schemas
class AlertBase(BaseModel):
    monitor_id: UUID
    type: str
    severity: str
    title: str
    message: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None

class Alert(AlertBase):
    id: UUID
    status: str
    resolution: Optional[str] = None
    resolution_time: Optional[float] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    channels: List[str] = Field(default_factory=list)
    notification_status: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Response schemas
class CollectionResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class ProcessingResponse(BaseModel):
    pipeline_run_id: UUID
    status: str
    progress: float
    current_task: Optional[str] = None
    results: Optional[Dict[str, Any]] = None

class MonitoringResponse(BaseModel):
    status: str
    metrics: Dict[str, Any]
    alerts: List[Alert] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

# Aggregated Status schemas
class SystemStatus(BaseModel):
    sources: Dict[str, str]
    pipelines: Dict[str, str]
    monitors: Dict[str, str]
    active_jobs: int
    pending_jobs: int
    error_count: int
    total_records_today: int
    avg_job_duration: float
    system_health: str

class DataQualityMetrics(BaseModel):
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    uniqueness: float
    validity: float
    integrity: float

class SystemMetrics(BaseModel):
    collection_rate: float
    processing_rate: float
    error_rate: float
    latency: float
    throughput: float
    success_rate: float
    resource_utilization: Dict[str, float]
