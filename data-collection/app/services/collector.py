from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
from uuid import UUID

from app.config.settings import settings
from app.models.data import (
    DataSource,
    CollectionJob,
    DataSet,
    Pipeline,
    Monitor,
    Alert
)
from app.schemas.data import (
    CollectionResponse,
    ProcessingResponse,
    MonitoringResponse,
    DataQualityMetrics,
    SystemMetrics
)
from app.services.pipeline import DataPipeline
from app.utils.validators import validate_data_quality

class DataCollectionService:
    def __init__(self):
        """Initialize data collection service"""
        self.session = None
        self.pipeline = DataPipeline()
        self.active_jobs: Dict[UUID, asyncio.Task] = {}
        self.rate_limiters: Dict[str, asyncio.Semaphore] = {}
        
        # Initialize rate limiters for each source
        for source in settings.DATA_SOURCES:
            self.rate_limiters[source] = asyncio.Semaphore(
                settings.MAX_CONCURRENT_TASKS
            )

    async def init_service(self):
        """Initialize HTTP session and connections"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

        # Cancel active jobs
        for job_id, task in self.active_jobs.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def create_collection_job(
        self,
        source_id: UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> CollectionJob:
        """Create a new data collection job"""
        try:
            # Get source config
            source_query = select(DataSource).where(DataSource.id == source_id)
            source = (await db.execute(source_query)).scalar_one()
            
            if not source.is_active:
                raise ValueError(f"Data source {source.name} is not active")

            # Create job
            job = CollectionJob(
                source_id=source_id,
                job_type="collection",
                params=params,
                status="pending",
                batch_size=params.get("batch_size", settings.BATCH_SIZE)
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)

            # Start collection in background
            task = asyncio.create_task(
                self._run_collection_job(job.id, db)
            )
            self.active_jobs[job.id] = task

            return job

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating collection job: {str(e)}")
            raise

    async def _run_collection_job(
        self,
        job_id: UUID,
        db: AsyncSession
    ) -> None:
        """Run data collection job"""
        try:
            # Get job details
            job_query = select(CollectionJob).where(CollectionJob.id == job_id)
            job = (await db.execute(job_query)).scalar_one()
            
            # Update job status
            job.status = "running"
            job.start_time = datetime.utcnow()
            await db.commit()

            # Get source config
            source_query = select(DataSource).where(
                DataSource.id == job.source_id
            )
            source = (await db.execute(source_query)).scalar_one()

            # Acquire rate limiter
            async with self.rate_limiters[source.type]:
                # Collect data in batches
                current_batch = 0
                total_records = 0
                batch_times = []
                
                while True:
                    batch_start = datetime.utcnow()
                    
                    # Collect batch
                    try:
                        batch_data = await self._collect_batch(
                            source,
                            job.params,
                            current_batch,
                            job.batch_size
                        )
                        
                        if not batch_data:
                            break
                            
                        # Process and validate batch
                        validated_data = await self._validate_batch(
                            batch_data,
                            source.config.get("validation_rules", {})
                        )
                        
                        # Store batch
                        await self._store_batch(
                            validated_data,
                            job,
                            current_batch,
                            db
                        )
                        
                        # Update metrics
                        batch_time = (datetime.utcnow() - batch_start).total_seconds()
                        batch_times.append(batch_time)
                        
                        records_in_batch = len(validated_data)
                        total_records += records_in_batch
                        
                        job.metrics = {
                            "records_processed": total_records,
                            "records_succeeded": total_records,
                            "avg_batch_time": sum(batch_times) / len(batch_times)
                        }
                        
                        # Update progress
                        if job.params.get("limit"):
                            progress = min(1.0, total_records / job.params["limit"])
                        else:
                            progress = 0.99  # Unknown total
                            
                        job.progress = progress
                        await db.commit()
                        
                        current_batch += 1
                        
                        if job.params.get("limit") and total_records >= job.params["limit"]:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing batch {current_batch}: {str(e)}")
                        job.error_details.append({
                            "batch": current_batch,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        await db.commit()
                        
                        if len(job.error_details) >= settings.MAX_ERRORS_BEFORE_SHUTDOWN:
                            raise Exception("Too many errors, stopping collection")

            # Update final status
            job.status = "completed"
            job.end_time = datetime.utcnow()
            job.processing_time = (job.end_time - job.start_time).total_seconds()
            await db.commit()

            # Run quality checks
            await self._run_quality_checks(job_id, db)

        except Exception as e:
            logger.error(f"Error running collection job {job_id}: {str(e)}")
            try:
                job.status = "failed"
                job.error_details.append({
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                await db.commit()
            except:
                pass
            raise
        finally:
            self.active_jobs.pop(job_id, None)

    async def _collect_batch(
        self,
        source: DataSource,
        params: Dict[str, Any],
        batch_num: int,
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """Collect batch of data from source"""
        try:
            # Add batch parameters
            batch_params = params.copy()
            batch_params.update({
                "offset": batch_num * batch_size,
                "limit": batch_size
            })

            # Set up request
            headers = source.config.get("headers", {})
            if source.credentials.get("api_key"):
                headers["Authorization"] = f"Bearer {source.credentials['api_key']}"

            # Make request
            async with self.session.get(
                source.config["url"],
                params=batch_params,
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(
                        f"Error collecting batch: {response.status} - {await response.text()}"
                    )

        except Exception as e:
            logger.error(f"Error collecting batch: {str(e)}")
            raise

    async def _validate_batch(
        self,
        data: List[Dict[str, Any]],
        rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate batch data"""
        validated_data = []
        
        for record in data:
            try:
                # Apply validation rules
                if validate_data_quality(record, rules):
                    validated_data.append(record)
            except Exception as e:
                logger.warning(f"Invalid record: {str(e)}")
                continue
                
        return validated_data

    async def _store_batch(
        self,
        data: List[Dict[str, Any]],
        job: CollectionJob,
        batch_num: int,
        db: AsyncSession
    ) -> None:
        """Store batch data"""
        try:
            # Create dataset if first batch
            if batch_num == 0:
                dataset = DataSet(
                    source_id=job.source_id,
                    collection_job_id=job.id,
                    name=f"collection_{job.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    type="raw",
                    format="json",
                    status="collecting"
                )
                db.add(dataset)
                await db.commit()
            
            # Store data in object storage
            batch_key = f"{job.id}/batch_{batch_num}.json"
            await self._store_in_minio(batch_key, data)
            
        except Exception as e:
            logger.error(f"Error storing batch: {str(e)}")
            raise

    async def _run_quality_checks(
        self,
        job_id: UUID,
        db: AsyncSession
    ) -> None:
        """Run data quality checks on collected data"""
        try:
            # Get job details
            job_query = select(CollectionJob).where(CollectionJob.id == job_id)
            job = (await db.execute(job_query)).scalar_one()
            
            # Calculate quality metrics
            metrics = await self._calculate_quality_metrics(job_id)
            
            # Update job metrics
            job.quality_metrics = metrics.model_dump()
            await db.commit()
            
            # Create alerts if quality issues found
            if metrics.accuracy < settings.MIN_QUALITY_SCORE:
                await self._create_quality_alert(
                    job_id,
                    "Low data accuracy",
                    f"Data accuracy score {metrics.accuracy:.2f} is below threshold",
                    db
                )
                
        except Exception as e:
            logger.error(f"Error running quality checks: {str(e)}")
            raise

    async def _calculate_quality_metrics(
        self,
        job_id: UUID
    ) -> DataQualityMetrics:
        """Calculate data quality metrics"""
        try:
            # Load all batches for job
            data = await self._load_job_data(job_id)
            
            if not data:
                raise ValueError("No data found for job")
                
            df = pd.DataFrame(data)
            
            # Calculate metrics
            metrics = DataQualityMetrics(
                completeness=df.notna().mean().mean(),
                accuracy=0.95,  # TODO: Implement accuracy checks
                consistency=0.90,  # TODO: Implement consistency checks
                timeliness=1.0,  # All data is fresh
                uniqueness=1 - df.duplicated().mean(),
                validity=0.95,  # TODO: Implement validation checks
                integrity=1.0  # TODO: Implement integrity checks
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {str(e)}")
            raise

    async def get_collection_status(
        self,
        job_id: UUID,
        db: AsyncSession
    ) -> CollectionResponse:
        """Get status of collection job"""
        try:
            job_query = select(CollectionJob).where(CollectionJob.id == job_id)
            job = (await db.execute(job_query)).scalar_one()
            
            return CollectionResponse(
                job_id=job.id,
                status=job.status,
                message=f"Collection job is {job.status}",
                data={
                    "progress": job.progress,
                    "metrics": job.metrics,
                    "error_details": job.error_details
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting collection status: {str(e)}")
            raise

    async def get_system_metrics(
        self,
        db: AsyncSession
    ) -> SystemMetrics:
        """Get system-wide metrics"""
        try:
            # Calculate metrics from recent jobs
            jobs_query = select(CollectionJob).where(
                CollectionJob.created_at >= datetime.utcnow() - pd.Timedelta(hours=24)
            )
            jobs = (await db.execute(jobs_query)).scalars().all()
            
            if not jobs:
                return SystemMetrics(
                    collection_rate=0,
                    processing_rate=0,
                    error_rate=0,
                    latency=0,
                    throughput=0,
                    success_rate=1,
                    resource_utilization={}
                )
            
            # Calculate metrics
            total_jobs = len(jobs)
            successful_jobs = len([j for j in jobs if j.status == "completed"])
            failed_jobs = len([j for j in jobs if j.status == "failed"])
            avg_duration = sum(
                (j.end_time - j.start_time).total_seconds() 
                for j in jobs 
                if j.end_time and j.start_time
            ) / total_jobs if total_jobs > 0 else 0
            
            total_records = sum(
                j.metrics.get("records_processed", 0)
                for j in jobs
            )
            
            return SystemMetrics(
                collection_rate=total_records / (24 * 60 * 60),  # Records per second
                processing_rate=total_records / (avg_duration if avg_duration > 0 else 1),
                error_rate=failed_jobs / total_jobs if total_jobs > 0 else 0,
                latency=avg_duration,
                throughput=total_records / (24 * 60 * 60),  # Records per second
                success_rate=successful_jobs / total_jobs if total_jobs > 0 else 1,
                resource_utilization={
                    "cpu": 0.5,  # TODO: Implement actual monitoring
                    "memory": 0.4,
                    "disk": 0.3
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            raise

    async def _create_quality_alert(
        self,
        job_id: UUID,
        title: str,
        message: str,
        db: AsyncSession
    ) -> None:
        """Create data quality alert"""
        try:
            alert = Alert(
                type="quality",
                severity="high",
                title=title,
                message=message,
                context={
                    "job_id": str(job_id)
                },
                occurred_at=datetime.utcnow()
            )
            
            db.add(alert)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            raise

    async def _store_in_minio(
        self,
        key: str,
        data: Any
    ) -> None:
        """Store data in MinIO"""
        try:
            from minio import Minio
            import json
            import io
            
            client = Minio(
                f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Convert data to JSON
            json_data = json.dumps(data)
            data_bytes = json_data.encode('utf-8')
            data_stream = io.BytesIO(data_bytes)
            
            # Upload to MinIO
            client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=key,
                data=data_stream,
                length=len(data_bytes),
                content_type='application/json'
            )
            
        except Exception as e:
            logger.error(f"Error storing in MinIO: {str(e)}")
            raise

    async def _load_job_data(
        self,
        job_id: UUID
    ) -> List[Dict[str, Any]]:
        """Load all data for a job from MinIO"""
        try:
            from minio import Minio
            import json
            
            client = Minio(
                f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # List all batch objects
            objects = client.list_objects(
                bucket_name=settings.MINIO_BUCKET,
                prefix=f"{job_id}/"
            )
            
            all_data = []
            for obj in objects:
                # Get object data
                data = client.get_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=obj.object_name
                )
                
                # Parse JSON
                batch_data = json.loads(data.read())
                all_data.extend(batch_data)
                
            return all_data
            
        except Exception as e:
            logger.error(f"Error loading job data: {str(e)}")
            raise
