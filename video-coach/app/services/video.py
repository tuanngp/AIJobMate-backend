from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import asyncio
from datetime import datetime
import os
import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from moviepy.editor import VideoFileClip
import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.video import VideoSession, User
from app.schemas.video import (
    VideoSessionCreate,
    VideoAnalysisResponse,
    Resolution,
    PerformanceMetrics
)
from app.services.ai import AIService
from app.config.settings import settings

class VideoService:
    def __init__(self, ai_service: AIService = AIService()):
        """Initialize video service"""
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
        session_data: VideoSessionCreate
    ) -> VideoSession:
        """Create a new video session"""
        try:
            session = VideoSession(**session_data.model_dump())
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating video session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create video session"
            )

    async def upload_video(
        self,
        file: UploadFile,
        session_id: UUID,
        db: AsyncSession
    ) -> Tuple[str, str, float, Resolution]:
        """Upload video file to S3 and extract metadata"""
        try:
            # Read file content
            content = await file.read()
            file_extension = file.filename.split('.')[-1].lower()

            if file_extension not in settings.SUPPORTED_VIDEO_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported video format. Supported formats: {settings.SUPPORTED_VIDEO_FORMATS}"
                )

            # Save temporarily for processing
            temp_path = f"/tmp/video-uploads/{session_id}.{file_extension}"
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as temp_file:
                temp_file.write(content)

            # Extract video metadata
            metadata = await self._extract_video_metadata(temp_path)

            if metadata["duration"] > settings.MAX_VIDEO_LENGTH:
                os.remove(temp_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"Video length exceeds maximum allowed ({settings.MAX_VIDEO_LENGTH} seconds)"
                )

            # Generate thumbnail
            thumbnail_path = f"/tmp/video-uploads/{session_id}_thumbnail.jpg"
            thumbnail_url = await self._generate_thumbnail(temp_path, thumbnail_path)

            # Upload to S3
            s3_key = f"interviews/{session_id}/{file.filename}"
            self.s3_client.upload_file(
                temp_path,
                settings.AWS_S3_BUCKET,
                s3_key
            )

            # Upload thumbnail
            if thumbnail_url:
                s3_thumb_key = f"interviews/{session_id}/thumbnail.jpg"
                self.s3_client.upload_file(
                    thumbnail_path,
                    settings.AWS_S3_BUCKET,
                    s3_thumb_key
                )
                thumbnail_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.AWS_S3_BUCKET,
                        'Key': s3_thumb_key
                    },
                    ExpiresIn=3600
                )

            # Generate presigned URL
            video_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET,
                    'Key': s3_key
                },
                ExpiresIn=3600
            )

            # Clean up temp files
            os.remove(temp_path)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)

            # Update session with video details
            stmt = select(VideoSession).where(VideoSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            session.video_url = video_url
            session.thumbnail_url = thumbnail_url
            session.duration = metadata["duration"]
            session.file_format = file_extension
            session.frame_count = metadata["frame_count"]
            session.resolution = metadata["resolution"].model_dump()
            await db.commit()

            return video_url, thumbnail_url, metadata["duration"], metadata["resolution"]

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise

    async def _extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract metadata from video file"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError("Could not open video file")

            # Get basic properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps

            cap.release()

            return {
                "duration": duration,
                "frame_count": frame_count,
                "fps": fps,
                "resolution": Resolution(width=width, height=height)
            }

        except Exception as e:
            logger.error(f"Error extracting video metadata: {str(e)}")
            raise

    async def _generate_thumbnail(
        self,
        video_path: str,
        output_path: str
    ) -> Optional[str]:
        """Generate thumbnail from video"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None

            # Seek to 1 second or 25% of duration, whichever is less
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            seek_frame = min(int(fps), int(total_frames * 0.25))
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
            ret, frame = cap.read()
            
            if ret:
                # Resize if needed
                max_size = 1280
                height, width = frame.shape[:2]
                if width > max_size or height > max_size:
                    scale = max_size / max(width, height)
                    frame = cv2.resize(frame, None, fx=scale, fy=scale)

                # Save thumbnail
                cv2.imwrite(output_path, frame)
                return output_path

            return None

        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return None
        finally:
            if 'cap' in locals():
                cap.release()

    async def process_video(
        self,
        session_id: UUID,
        db: AsyncSession,
        redis: Redis
    ) -> VideoAnalysisResponse:
        """Process video and generate analysis"""
        try:
            # Get session
            stmt = select(VideoSession).where(VideoSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            processing_start = datetime.utcnow()

            # Create processing directory
            frames_dir = f"{settings.FRAMES_DIR}/{session_id}"
            os.makedirs(frames_dir, exist_ok=True)

            try:
                # Download video from S3
                temp_path = f"/tmp/video-uploads/{session_id}.{session.file_format}"
                self.s3_client.download_file(
                    settings.AWS_S3_BUCKET,
                    session.video_url.split('?')[0].split(settings.AWS_S3_BUCKET + '/')[-1],
                    temp_path
                )

                # Extract and analyze frames
                facial_expressions, posture_metrics, gestures = await self._analyze_video_frames(
                    temp_path,
                    frames_dir,
                    session
                )

                # Clean up temp files
                os.remove(temp_path)
                import shutil
                shutil.rmtree(frames_dir)

                # Calculate performance metrics
                performance_metrics = await self._calculate_performance_metrics(
                    facial_expressions,
                    posture_metrics,
                    gestures
                )

                # Generate feedback
                feedback, recommendations, practice_suggestions = await self.ai_service.generate_feedback(
                    facial_expressions,
                    posture_metrics,
                    gestures,
                    performance_metrics
                )

                # Update session with results
                session.facial_expressions = {
                    str(idx): expr.model_dump() 
                    for idx, expr in enumerate(facial_expressions)
                }
                session.posture_analysis = {
                    str(idx): metric.model_dump() 
                    for idx, metric in enumerate(posture_metrics)
                }
                session.gesture_analysis = {
                    str(idx): gesture.model_dump() 
                    for idx, gesture in enumerate(gestures)
                }
                session.performance_metrics = performance_metrics.model_dump()
                session.feedback = feedback
                session.recommendations = recommendations
                session.practice_suggestions = practice_suggestions
                session.is_processed = True
                session.processed_at = datetime.utcnow()

                await db.commit()

                # Calculate processing time
                processing_time = (datetime.utcnow() - processing_start).total_seconds()

                # Prepare response
                response = VideoAnalysisResponse(
                    session_id=session_id,
                    performance_metrics=performance_metrics,
                    facial_analysis=session.facial_expressions,
                    body_language_analysis={
                        "posture": session.posture_analysis,
                        "gestures": session.gesture_analysis
                    },
                    key_moments=[],  # TODO: Implement key moments detection
                    feedback=feedback,
                    recommendations=recommendations,
                    practice_suggestions=practice_suggestions,
                    processing_time=processing_time
                )

                # Cache results
                cache_key = f"video_analysis:{session_id}"
                await redis.set(
                    cache_key,
                    response.model_dump_json(),
                    ex=settings.CACHE_EXPIRE_TIME
                )

                return response

            except Exception as e:
                logger.error(f"Error processing video: {str(e)}")
                session.is_processed = True
                session.processing_error = str(e)
                await db.commit()
                raise

        except Exception as e:
            logger.error(f"Error in process_video: {str(e)}")
            raise

    async def _analyze_video_frames(
        self,
        video_path: str,
        frames_dir: str,
        session: VideoSession
    ) -> Tuple[List[Any], List[Any], List[Any]]:
        """Extract and analyze frames from video"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file")

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Analysis results
            facial_expressions = []
            posture_metrics = []
            gestures = []
            
            # Process frames at specified rate
            frame_interval = int(fps / settings.FRAME_EXTRACTION_RATE)
            
            for frame_idx in range(0, total_frames, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    break

                timestamp = frame_idx / fps

                # Analyze frame
                if settings.ANALYZE_FACIAL_EXPRESSIONS:
                    expr = await self.ai_service.analyze_facial_expressions(frame, timestamp)
                    if expr:
                        facial_expressions.append(expr)

                if settings.ANALYZE_BODY_LANGUAGE:
                    posture = await self.ai_service.analyze_posture(frame, timestamp)
                    if posture:
                        posture_metrics.append(posture)

                if settings.ANALYZE_GESTURES:
                    gesture = await self.ai_service.analyze_gestures(frame, timestamp)
                    if gesture:
                        gestures.append(gesture)

            cap.release()
            return facial_expressions, posture_metrics, gestures

        except Exception as e:
            logger.error(f"Error analyzing video frames: {str(e)}")
            raise

    async def _calculate_performance_metrics(
        self,
        facial_expressions: List[Any],
        posture_metrics: List[Any],
        gestures: List[Any]
    ) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        try:
            if not facial_expressions and not posture_metrics:
                raise ValueError("No analysis data available")

            # Calculate confidence score (based on facial expressions and gestures)
            confidence_components = []
            if facial_expressions:
                avg_eye_contact = np.mean([expr.eye_contact for expr in facial_expressions])
                positive_emotions = np.mean([
                    expr.emotions.get("confident", 0) + expr.emotions.get("happy", 0)
                    for expr in facial_expressions
                ])
                confidence_components.extend([avg_eye_contact, positive_emotions])

            if gestures:
                gesture_confidence = np.mean([g.confidence for g in gestures])
                confidence_components.append(gesture_confidence)

            confidence_score = np.mean(confidence_components) * 100 if confidence_components else 0

            # Calculate engagement score
            engagement_components = []
            if facial_expressions:
                emotion_variety = len(set(
                    max(expr.emotions.items(), key=lambda x: x[1])[0]
                    for expr in facial_expressions
                ))
                engagement_components.append(emotion_variety / 5)  # Normalize by typical emotion count

            if posture_metrics:
                avg_stability = np.mean([m.stability for m in posture_metrics])
                engagement_components.append(avg_stability)

            engagement_score = np.mean(engagement_components) * 100 if engagement_components else 0

            # Calculate professionalism score
            professionalism_components = []
            if posture_metrics:
                avg_alignment = np.mean([m.alignment for m in posture_metrics])
                professionalism_components.append(avg_alignment)

            if facial_expressions:
                professional_ratio = np.mean([
                    1 - (expr.emotions.get("angry", 0) + expr.emotions.get("nervous", 0))
                    for expr in facial_expressions
                ])
                professionalism_components.append(professional_ratio)

            professionalism_score = np.mean(professionalism_components) * 100 if professionalism_components else 0

            # Calculate overall score
            overall_score = np.mean([
                confidence_score * 0.3,
                engagement_score * 0.3,
                professionalism_score * 0.4
            ])

            section_scores = {
                "eye_contact": avg_eye_contact * 100 if facial_expressions else 0,
                "emotion_expression": positive_emotions * 100 if facial_expressions else 0,
                "posture_stability": avg_stability * 100 if posture_metrics else 0,
                "gesture_effectiveness": gesture_confidence * 100 if gestures else 0
            }

            return PerformanceMetrics(
                confidence_score=confidence_score,
                engagement_score=engagement_score,
                professionalism_score=professionalism_score,
                overall_score=overall_score,
                section_scores=section_scores
            )

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            raise
