from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.config.settings import settings
from app.models.data import Pipeline, PipelineRun, DataSet, Alert
from app.schemas.data import (
    ProcessingResponse,
    PipelineConfig,
    TaskConfig,
    TaskResult
)
from app.utils.validators import validate_data_quality

class DataPipeline:
    def __init__(self):
        """Initialize data pipeline service"""
        self.active_pipelines: Dict[UUID, asyncio.Task] = {}
        self.task_registry: Dict[str, Any] = self._register_tasks()

    def _register_tasks(self) -> Dict[str, Any]:
        """Register available pipeline tasks"""
        return {
            "clean_data": self._clean_data,
            "validate_data": self._validate_data,
            "transform_data": self._transform_data,
            "analyze_data": self._analyze_data,
            "aggregate_data": self._aggregate_data,
            "export_data": self._export_data,
            "generate_report": self._generate_report
        }

    async def create_pipeline(
        self,
        config: PipelineConfig,
        db: AsyncSession
    ) -> Pipeline:
        """Create a new data pipeline"""
        try:
            # Validate pipeline configuration
            self._validate_pipeline_config(config)
            
            # Create pipeline
            pipeline = Pipeline(
                name=config.name,
                description=config.description,
                config=config.model_dump(),
                is_active=True
            )
            
            db.add(pipeline)
            await db.commit()
            await db.refresh(pipeline)
            
            return pipeline

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating pipeline: {str(e)}")
            raise

    async def run_pipeline(
        self,
        pipeline_id: UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> PipelineRun:
        """Run a data pipeline"""
        try:
            # Get pipeline
            pipeline_query = select(Pipeline).where(Pipeline.id == pipeline_id)
            pipeline = (await db.execute(pipeline_query)).scalar_one()
            
            if not pipeline.is_active:
                raise ValueError(f"Pipeline {pipeline.name} is not active")

            # Create pipeline run
            run = PipelineRun(
                pipeline_id=pipeline_id,
                trigger_type="manual",
                params=params,
                status="pending",
                start_time=datetime.utcnow()
            )
            
            db.add(run)
            await db.commit()
            await db.refresh(run)

            # Start pipeline in background
            task = asyncio.create_task(
                self._execute_pipeline(run.id, db)
            )
            self.active_pipelines[run.id] = task

            return run

        except Exception as e:
            await db.rollback()
            logger.error(f"Error starting pipeline: {str(e)}")
            raise

    async def _execute_pipeline(
        self,
        run_id: UUID,
        db: AsyncSession
    ) -> None:
        """Execute pipeline tasks"""
        try:
            # Get run details
            run_query = select(PipelineRun).where(PipelineRun.id == run_id)
            run = (await db.execute(run_query)).scalar_one()
            
            # Get pipeline config
            pipeline_query = select(Pipeline).where(
                Pipeline.id == run.pipeline_id
            )
            pipeline = (await db.execute(pipeline_query)).scalar_one()
            
            # Update status
            run.status = "running"
            await db.commit()

            # Execute tasks in order
            tasks = pipeline.config["tasks"]
            total_tasks = len(tasks)
            completed_tasks = 0
            
            for task_config in tasks:
                try:
                    # Update current task
                    run.current_task = task_config["name"]
                    await db.commit()
                    
                    # Execute task
                    task_func = self.task_registry.get(task_config["type"])
                    if not task_func:
                        raise ValueError(f"Unknown task type: {task_config['type']}")
                        
                    result = await task_func(
                        task_config["config"],
                        run.params,
                        db
                    )
                    
                    # Store task result
                    run.task_results[task_config["name"]] = TaskResult(
                        status="completed",
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        metrics=result
                    ).model_dump()
                    
                    completed_tasks += 1
                    run.progress = completed_tasks / total_tasks
                    await db.commit()
                    
                except Exception as e:
                    logger.error(f"Error in task {task_config['name']}: {str(e)}")
                    run.task_results[task_config["name"]] = TaskResult(
                        status="failed",
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        error={"message": str(e)}
                    ).model_dump()
                    raise

            # Update final status
            run.status = "completed"
            run.end_time = datetime.utcnow()
            run.duration = (run.end_time - run.start_time).total_seconds()
            await db.commit()

            # Update pipeline metrics
            await self._update_pipeline_metrics(pipeline.id, run, db)

        except Exception as e:
            logger.error(f"Error executing pipeline {run_id}: {str(e)}")
            try:
                run.status = "failed"
                run.error = {"message": str(e)}
                run.end_time = datetime.utcnow()
                await db.commit()
            except:
                pass
            raise
        finally:
            self.active_pipelines.pop(run_id, None)

    async def _clean_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Clean and preprocess data"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            # Apply cleaning rules
            if config.get("remove_duplicates"):
                df = df.drop_duplicates()
                
            if config.get("fill_missing_values"):
                df = df.fillna(config["fill_values"])
                
            if config.get("remove_outliers"):
                df = self._remove_outliers(df, config["outlier_columns"])

            # Store cleaned data
            cleaned_data = df.to_dict("records")
            await self._store_data(
                params["output_dataset_id"],
                cleaned_data,
                "cleaned"
            )
            
            return {
                "input_rows": len(data),
                "output_rows": len(cleaned_data),
                "duplicates_removed": len(data) - len(cleaned_data),
                "missing_values_filled": df.isna().sum().sum()
            }

        except Exception as e:
            logger.error(f"Error cleaning data: {str(e)}")
            raise

    async def _validate_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Validate data quality"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            
            # Apply validation rules
            validation_results = []
            for record in data:
                result = validate_data_quality(record, config["rules"])
                validation_results.append(result)
                
            # Calculate metrics
            total = len(validation_results)
            passed = sum(1 for r in validation_results if r["valid"])
            failed = total - passed
            
            return {
                "total_records": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed / total if total > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            raise

    async def _transform_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Transform data according to rules"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            transformations = 0
            
            # Apply transformations
            for transform in config["transformations"]:
                if transform["type"] == "rename":
                    df = df.rename(columns=transform["mapping"])
                    transformations += len(transform["mapping"])
                    
                elif transform["type"] == "cast":
                    for col, dtype in transform["dtypes"].items():
                        df[col] = df[col].astype(dtype)
                    transformations += len(transform["dtypes"])
                    
                elif transform["type"] == "derive":
                    for col, expr in transform["expressions"].items():
                        df[col] = df.eval(expr)
                    transformations += len(transform["expressions"])

            # Store transformed data
            transformed_data = df.to_dict("records")
            await self._store_data(
                params["output_dataset_id"],
                transformed_data,
                "transformed"
            )
            
            return {
                "input_columns": len(data[0]) if data else 0,
                "output_columns": len(df.columns),
                "transformations_applied": transformations
            }

        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            raise

    async def _analyze_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze data and generate insights"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            analysis = {}
            
            # Statistical analysis
            if config.get("statistics"):
                analysis["statistics"] = {
                    "numeric": df.describe().to_dict(),
                    "categorical": {
                        col: df[col].value_counts().to_dict()
                        for col in df.select_dtypes(include=["object"]).columns
                    }
                }
                
            # Time series analysis
            if config.get("time_series") and "date_column" in config:
                df[config["date_column"]] = pd.to_datetime(df[config["date_column"]])
                analysis["time_series"] = {
                    "trend": df.groupby(
                        df[config["date_column"]].dt.to_period(config["frequency"])
                    ).size().to_dict()
                }
                
            # Correlation analysis
            if config.get("correlations"):
                analysis["correlations"] = df.corr().to_dict()
                
            return {
                "analysis_type": list(analysis.keys()),
                "metrics_generated": sum(len(v) for v in analysis.values()),
                "insights": analysis
            }

        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            raise

    async def _aggregate_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Aggregate data according to rules"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            # Apply aggregations
            grouped = df.groupby(config["group_by"])
            aggregated = grouped.agg(config["aggregations"])
            
            # Store aggregated data
            agg_data = aggregated.reset_index().to_dict("records")
            await self._store_data(
                params["output_dataset_id"],
                agg_data,
                "aggregated"
            )
            
            return {
                "input_rows": len(df),
                "output_rows": len(aggregated),
                "group_by_columns": config["group_by"],
                "aggregation_functions": config["aggregations"]
            }

        except Exception as e:
            logger.error(f"Error aggregating data: {str(e)}")
            raise

    async def _export_data(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Export data to various formats"""
        try:
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            exports = []
            
            for export in config["exports"]:
                if export["format"] == "csv":
                    output = df.to_csv(**export.get("options", {}))
                    
                elif export["format"] == "parquet":
                    output = df.to_parquet(**export.get("options", {}))
                    
                elif export["format"] == "json":
                    output = df.to_json(**export.get("options", {}))
                
                # Store exported file
                await self._store_export(
                    export["location"],
                    output,
                    export["format"]
                )
                exports.append(export["location"])
            
            return {
                "exports": exports,
                "formats": [e["format"] for e in config["exports"]],
                "total_bytes": sum(len(e) for e in exports)
            }

        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise

    async def _generate_report(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Generate data quality report"""
        try:
            from ydata_profiling import ProfileReport
            
            # Load data
            data = await self._load_data(params["dataset_id"])
            df = pd.DataFrame(data)
            
            # Generate profile report
            profile = ProfileReport(
                df,
                title=config.get("title", "Data Quality Report"),
                minimal=config.get("minimal", False)
            )
            
            # Save report
            report_location = f"reports/{params['dataset_id']}_report.html"
            profile.to_file(report_location)
            
            # Extract key metrics
            metrics = profile.get_description()
            
            return {
                "report_location": report_location,
                "total_records": len(df),
                "total_features": len(df.columns),
                "quality_metrics": metrics
            }

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _validate_pipeline_config(self, config: PipelineConfig) -> None:
        """Validate pipeline configuration"""
        try:
            # Check task types
            for task in config.tasks:
                if task.type not in self.task_registry:
                    raise ValueError(f"Unknown task type: {task.type}")

            # Check task dependencies
            task_names = {task.name for task in config.tasks}
            for task in config.tasks:
                for dep in task.dependencies:
                    if dep not in task_names:
                        raise ValueError(f"Unknown dependency {dep} for task {task.name}")

            # Check for cycles in dependencies
            self._check_dependency_cycles(config.tasks)

        except Exception as e:
            logger.error(f"Invalid pipeline configuration: {str(e)}")
            raise

    def _check_dependency_cycles(self, tasks: List[TaskConfig]) -> None:
        """Check for cycles in task dependencies"""
        def has_cycle(task: str, visited: set, stack: set) -> bool:
            if task in stack:
                return True
            if task in visited:
                return False
                
            visited.add(task)
            stack.add(task)
            
            task_config = next(t for t in tasks if t.name == task)
            for dep in task_config.dependencies:
                if has_cycle(dep, visited, stack):
                    return True
                    
            stack.remove(task)
            return False

        visited = set()
        stack = set()
        
        for task in tasks:
            if has_cycle(task.name, visited, stack):
                raise ValueError(f"Cycle detected in pipeline dependencies")

    def _remove_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Remove outliers using IQR method"""
        for col in columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            df = df[
                (df[col] >= Q1 - 1.5 * IQR) & 
                (df[col] <= Q3 + 1.5 * IQR)
            ]
            
        return df

    async def _store_data(
        self,
        dataset_id: UUID,
        data: List[Dict[str, Any]],
        data_type: str
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
            key = f"{dataset_id}/{data_type}.json"
            client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=key,
                data=data_stream,
                length=len(data_bytes),
                content_type='application/json'
            )
            
        except Exception as e:
            logger.error(f"Error storing data: {str(e)}")
            raise

    async def _load_data(
        self,
        dataset_id: UUID
    ) -> List[Dict[str, Any]]:
        """Load data from MinIO"""
        try:
            from minio import Minio
            import json
            
            client = Minio(
                f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Get latest data file
            objects = client.list_objects(
                bucket_name=settings.MINIO_BUCKET,
                prefix=f"{dataset_id}/"
            )
            latest = sorted(objects, key=lambda x: x.last_modified)[-1]
            
            # Get object data
            data = client.get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=latest.object_name
            )
            
            # Parse JSON
            return json.loads(data.read())
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise

    async def _store_export(
        self,
        location: str,
        data: bytes,
        format: str
    ) -> None:
        """Store exported data"""
        try:
            from minio import Minio
            import io
            
            client = Minio(
                f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Upload to MinIO
            data_stream = io.BytesIO(data)
            client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=location,
                data=data_stream,
                length=len(data),
                content_type=f"application/{format}"
            )
            
        except Exception as e:
            logger.error(f"Error storing export: {str(e)}")
            raise

    async def _update_pipeline_metrics(
        self,
        pipeline_id: UUID,
        run: PipelineRun,
        db: AsyncSession
    ) -> None:
        """Update pipeline performance metrics"""
        try:
            pipeline_query = select(Pipeline).where(Pipeline.id == pipeline_id)
            pipeline = (await db.execute(pipeline_query)).scalar_one()
            
            # Update metrics
            if not pipeline.metrics:
                pipeline.metrics = {}
                
            runs_query = select(PipelineRun).where(
                PipelineRun.pipeline_id == pipeline_id
            )
            runs = (await db.execute(runs_query)).scalars().all()
            
            successful_runs = len([r for r in runs if r.status == "completed"])
            failed_runs = len([r for r in runs if r.status == "failed"])
            
            durations = [
                r.duration for r in runs 
                if r.duration is not None
            ]
            
            pipeline.metrics.update({
                "total_runs": len(runs),
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": successful_runs / len(runs) if runs else 0,
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "last_run": run.end_time.isoformat()
            })
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating pipeline metrics: {str(e)}")
            raise
