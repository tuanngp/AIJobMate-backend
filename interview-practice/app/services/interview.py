from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import asyncio
from datetime import datetime
import os
from fastapi import HTTPException, UploadFile
import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.interview import InterviewSession, User
from app.schemas.interview import (
    InterviewSessionCreate,
    InterviewAnalysisResponse,
    AudioMetadata,
    PerformanceMetrics
)
from app.services.ai import AIService
from app.config.settings import settings

class InterviewService:
    def __init__(self, ai_service: AIService = AIService()):
        """Initialize interview service"""
        self.ai_service = ai_service
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    async def create_session(
        self,
        db: AsyncSession,
        session_data: InterviewSessionCreate
    ) -> InterviewSession:
        """Create a new interview session"""
        try:
            session = InterviewSession(**session_data.model_dump())
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating interview session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create interview session"
            )

    async def upload_audio(
        self,
        file: UploadFile,
        session_id: UUID,
        db: AsyncSession
    ) -> Tuple[str, AudioMetadata]:
        """Upload audio file to S3 and update session"""
        try:
            # Read file content
            content = await file.read()
            file_extension = file.filename.split('.')[-1].lower()

            if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format. Supported formats: {settings.SUPPORTED_AUDIO_FORMATS}"
                )

            # Save temporarily for processing
            temp_path = f"/tmp/{session_id}.{file_extension}"
            with open(temp_path, "wb") as temp_file:
                temp_file.write(content)

            # Process audio file
            metadata, audio = await self.ai_service.process_audio(
                temp_path,
                file.filename
            )

            if metadata.duration > settings.MAX_AUDIO_LENGTH:
                os.remove(temp_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio length exceeds maximum allowed ({settings.MAX_AUDIO_LENGTH} seconds)"
                )

            # Upload to S3
            s3_key = f"interviews/{session_id}/{file.filename}"
            self.s3_client.upload_file(
                temp_path,
                settings.AWS_S3_BUCKET,
                s3_key
            )

            # Generate presigned URL
            audio_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET,
                    'Key': s3_key
                },
                ExpiresIn=3600  # 1 hour
            )

            # Clean up temp file
            os.remove(temp_path)

            # Update session with audio details
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            session.audio_url = audio_url
            session.duration = metadata.duration
            session.file_format = file_extension
            await db.commit()

            return audio_url, metadata

        except Exception as e:
            logger.error(f"Error uploading audio: {str(e)}")
            raise

    async def process_interview(
        self,
        session_id: UUID,
        db: AsyncSession,
        redis: Redis
    ) -> InterviewAnalysisResponse:
        """Process interview recording and generate analysis"""
        try:
            # Get session
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            processing_start = datetime.utcnow()

            # Download audio from S3
            temp_path = f"/tmp/{session_id}.{session.file_format}"
            self.s3_client.download_file(
                settings.AWS_S3_BUCKET,
                session.audio_url.split('?')[0].split(settings.AWS_S3_BUCKET + '/')[-1],
                temp_path
            )

            # Transcribe audio
            transcript = await self.ai_service.transcribe_audio(temp_path)
            session.transcript = transcript

            # Process audio for speech metrics
            metadata, audio = await self.ai_service.process_audio(
                temp_path,
                f"{session_id}.{session.file_format}"
            )
            speech_metrics = await self.ai_service.analyze_speech_metrics(
                audio,
                metadata.sample_rate
            )
            session.speech_metrics = speech_metrics.model_dump()

            # Clean up temp file
            os.remove(temp_path)

            # Analyze sentiment
            sentiment_analysis = await self.ai_service.analyze_sentiment(
                transcript,
                speech_metrics
            )
            session.sentiment_analysis = sentiment_analysis.model_dump()

            # Analyze content
            content_analysis = await self.ai_service.analyze_content(
                transcript,
                session.interview_type,
                session.job_role
            )
            session.content_analysis = content_analysis.model_dump()
            session.key_points = content_analysis.key_points

            # Calculate performance metrics
            performance_metrics = self.ai_service.calculate_performance_metrics(
                speech_metrics,
                sentiment_analysis,
                content_analysis
            )
            
            # Generate feedback
            feedback, recommendations, practice_suggestions = await self.ai_service.generate_feedback(
                speech_metrics,
                sentiment_analysis,
                content_analysis,
                performance_metrics
            )

            # Update session with results
            session.feedback = feedback
            session.recommendations = recommendations
            session.practice_suggestions = practice_suggestions
            session.performance_metrics = performance_metrics.model_dump()
            session.is_processed = True
            session.processed_at = datetime.utcnow()

            await db.commit()

            # Calculate processing time
            processing_time = (datetime.utcnow() - processing_start).total_seconds()

            # Prepare response
            response = InterviewAnalysisResponse(
                session_id=session_id,
                transcript=transcript,
                speech_analysis=speech_metrics.model_dump(),
                content_analysis=content_analysis.model_dump(),
                feedback=feedback,
                performance_metrics=performance_metrics,
                recommendations=recommendations,
                practice_suggestions=practice_suggestions,
                processing_time=processing_time
            )

            # Cache results
            cache_key = f"interview_analysis:{session_id}"
            await redis.set(
                cache_key,
                response.model_dump_json(),
                ex=settings.CACHE_EXPIRE_TIME
            )

            return response

        except Exception as e:
            logger.error(f"Error processing interview: {str(e)}")
            if 'session' in locals():
                session.is_processed = True
                session.processing_error = str(e)
                await db.commit()
            raise

    async def get_session_analysis(
        self,
        session_id: UUID,
        db: AsyncSession,
        redis: Redis
    ) -> InterviewAnalysisResponse:
        """Get interview analysis results"""
        # Try cache first
        cache_key = f"interview_analysis:{session_id}"
        cached = await redis.get(cache_key)
        if cached:
            return InterviewAnalysisResponse.model_validate_json(cached)

        # Get from database
        stmt = select(InterviewSession).where(InterviewSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.is_processed:
            raise HTTPException(
                status_code=202,
                detail="Interview analysis is still processing"
            )

        if session.processing_error:
            raise HTTPException(
                status_code=500,
                detail=session.processing_error
            )

        # Convert session data to response
        response = InterviewAnalysisResponse(
            session_id=session_id,
            transcript=session.transcript,
            speech_analysis=session.speech_metrics,
            content_analysis=session.content_analysis,
            feedback=session.feedback,
            performance_metrics=PerformanceMetrics(**session.performance_metrics),
            recommendations=session.recommendations,
            practice_suggestions=session.practice_suggestions,
            processing_time=0.0  # Not applicable for cached results
        )

        return response

    async def get_user_sessions(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> List[InterviewSession]:
        """Get all interview sessions for a user"""
        stmt = select(InterviewSession).where(
            InterviewSession.user_id == user_id
        ).order_by(InterviewSession.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_session(
        self,
        session_id: UUID,
        db: AsyncSession,
        redis: Redis
    ) -> bool:
        """Delete an interview session and its associated data"""
        try:
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                return False

            # Delete audio from S3 if exists
            if session.audio_url:
                try:
                    s3_key = session.audio_url.split('?')[0].split(settings.AWS_S3_BUCKET + '/')[-1]
                    self.s3_client.delete_object(
                        Bucket=settings.AWS_S3_BUCKET,
                        Key=s3_key
                    )
                except Exception as e:
                    logger.error(f"Error deleting S3 object: {str(e)}")

            # Delete from database
            await db.delete(session)
            await db.commit()

            # Clear cache
            cache_key = f"interview_analysis:{session_id}"
            await redis.delete(cache_key)

            return True

        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            await db.rollback()
            raise
