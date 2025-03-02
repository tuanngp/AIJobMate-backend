from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base

class DataSource(Base):
    """Data source configuration and status"""
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    type = Column(String)  # job_board, company_api, market_data, etc.
    config = Column(JSONB, default={})
    credentials = Column(JSONB, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime)
    last_success = Column(DateTime)
    error_count = Column(Integer, default=0)
    avg_response_time = Column(Float)
    
    # Rate limiting
    requests_per_second = Column(Float)
    requests_per_minute = Column(Integer)
    requests_per_hour = Column(Integer)
    
    # Metrics
    total_records = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    data_quality_score = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collection_jobs = relationship("CollectionJob", back_populates="source")
    data_sets = relationship("DataSet", back_populates="source")

class CollectionJob(Base):
    """Data collection job tracking"""
    __tablename__ = "collection_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"))
    job_type = Column(String)  # full_sync, incremental, validation
    
    # Parameters
    params = Column(JSONB, default={})
    filters = Column(JSONB, default={})
    batch_size = Column(Integer)
    
    # Status
    status = Column(String)  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    current_batch = Column(Integer, default=0)
    total_batches = Column(Integer)
    
    # Results
    records_processed = Column(Integer, default=0)
    records_succeeded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_details = Column(JSONB, default=[])
    
    # Performance
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    processing_time = Column(Float)
    avg_batch_time = Column(Float)
    
    # Quality metrics
    validation_score = Column(Float)
    quality_metrics = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = relationship("DataSource", back_populates="collection_jobs")
    data_sets = relationship("DataSet", back_populates="collection_job")

class DataSet(Base):
    """Collected and processed dataset"""
    __tablename__ = "data_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"))
    collection_job_id = Column(UUID(as_uuid=True), ForeignKey("collection_jobs.id"))
    
    # Dataset info
    name = Column(String)
    type = Column(String)  # raw, processed, aggregated
    format = Column(String)  # json, csv, parquet
    location = Column(String)  # S3/MinIO path
    
    # Schema and validation
    schema = Column(JSONB)
    validation_rules = Column(JSONB)
    required_fields = Column(ARRAY(String))
    
    # Statistics
    record_count = Column(Integer)
    file_size = Column(Integer)  # in bytes
    field_statistics = Column(JSONB)
    
    # Quality metrics
    completeness = Column(Float)  # % of non-null values
    accuracy = Column(Float)  # % of valid values
    consistency = Column(Float)  # % of consistent values
    uniqueness = Column(Float)  # % of unique values
    
    # Processing info
    processing_steps = Column(JSONB, default=[])
    transformations = Column(JSONB, default=[])
    data_lineage = Column(JSONB, default={})
    
    # Status
    status = Column(String)  # raw, processing, validated, available
    is_latest = Column(Boolean, default=False)
    
    # Timestamps
    collected_at = Column(DateTime)
    processed_at = Column(DateTime)
    validated_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = relationship("DataSource", back_populates="data_sets")
    collection_job = relationship("CollectionJob", back_populates="data_sets")

class Pipeline(Base):
    """Data pipeline configuration and status"""
    __tablename__ = "pipelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    
    # Configuration
    config = Column(JSONB, default={})
    schedule = Column(String)  # Cron expression
    timeout = Column(Integer)  # seconds
    retry_count = Column(Integer)
    
    # Components
    tasks = Column(JSONB)  # List of tasks
    dependencies = Column(JSONB)  # Task dependencies
    inputs = Column(JSONB)  # Input datasets
    outputs = Column(JSONB)  # Output datasets
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    running_since = Column(DateTime)
    
    # Performance
    avg_duration = Column(Float)
    success_rate = Column(Float)
    failure_count = Column(Integer, default=0)
    
    # Monitoring
    alerts = Column(JSONB, default=[])
    metrics = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    runs = relationship("PipelineRun", back_populates="pipeline")

class PipelineRun(Base):
    """Individual pipeline run tracking"""
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"))
    
    # Run info
    trigger_type = Column(String)  # scheduled, manual, api
    params = Column(JSONB, default={})
    
    # Status
    status = Column(String)  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    current_task = Column(String)
    error = Column(JSONB)
    
    # Results
    task_results = Column(JSONB, default={})
    metrics = Column(JSONB, default={})
    artifacts = Column(JSONB, default=[])
    
    # Performance
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    
    # Resource usage
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    
    # Logs and monitoring
    log_location = Column(String)
    trace_id = Column(String)
    alerts = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="runs")

class Monitor(Base):
    """Data quality and pipeline monitoring"""
    __tablename__ = "monitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    type = Column(String)  # quality, performance, anomaly, drift
    
    # Configuration
    config = Column(JSONB, default={})
    metrics = Column(ARRAY(String))
    thresholds = Column(JSONB)
    schedule = Column(String)
    
    # Rules
    validation_rules = Column(JSONB, default=[])
    alert_rules = Column(JSONB, default=[])
    
    # Status
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime)
    last_alert = Column(DateTime)
    
    # Results
    current_status = Column(String)  # healthy, warning, critical
    latest_results = Column(JSONB)
    historical_results = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Alert(Base):
    """System alerts and notifications"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id"))
    type = Column(String)  # error, warning, info
    severity = Column(String)  # critical, high, medium, low
    
    # Alert details
    title = Column(String)
    message = Column(Text)
    metrics = Column(JSONB)
    context = Column(JSONB)
    
    # Status
    status = Column(String)  # new, acknowledged, resolved
    acknowledged_by = Column(String)
    resolved_by = Column(String)
    
    # Resolution
    resolution = Column(Text)
    resolution_time = Column(Float)
    
    # Notifications
    channels = Column(ARRAY(String))
    notification_status = Column(JSONB, default={})
    
    # Timestamps
    occurred_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
