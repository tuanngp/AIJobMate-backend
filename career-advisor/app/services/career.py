from typing import List, Optional
from uuid import UUID
import asyncio
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis

from app.models.career import CareerAdvice, User
from app.services.ai import AIService
from app.config.settings import settings

class CareerService:
    def __init__(self, ai_service: AIService = AIService()):
        self.ai_service = ai_service

    async def create_cv_analysis(
        self,
        db: AsyncSession,
        file_content: bytes,
        file_name: str,
        user_id: Optional[UUID] = None
    ) -> CareerAdvice:
        """Create a new CV analysis entry"""
        try:
            # Convert CV content to text
            cv_text = file_content.decode('utf-8')

            # Create career advice entry
            career_advice = CareerAdvice(
                user_id=user_id,
                cv_text=cv_text,
                is_processed=False
            )

            db.add(career_advice)
            await db.commit()
            await db.refresh(career_advice)

            return career_advice

        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create CV analysis: {str(e)}"
            )

    async def process_cv_analysis(
        self,
        career_advice_id: UUID,
        db: AsyncSession,
        redis: Redis
    ):
        """Process CV analysis in background"""
        try:
            # Get career advice
            stmt = select(CareerAdvice).where(CareerAdvice.id == career_advice_id)
            result = await db.execute(stmt)
            career_advice = result.scalar_one_or_none()

            if not career_advice:
                raise HTTPException(status_code=404, detail="CV analysis not found")

            # Generate CV embedding
            embedding = await self.ai_service.generate_cv_embedding(career_advice.cv_text)
            career_advice.cv_embedding = embedding

            # Extract skills and interests
            skills_analysis = await self.ai_service.analyze_skills(career_advice.cv_text)
            career_advice.skills = skills_analysis.get("skills", [])
            career_advice.interests = skills_analysis.get("interests", [])

            # Analyze strengths and weaknesses
            analysis = await self.ai_service.analyze_cv(career_advice.cv_text)
            career_advice.strengths = analysis.get("strengths", [])
            career_advice.weaknesses = analysis.get("weaknesses", [])
            career_advice.improvement_areas = analysis.get("improvement_areas", {})

            # Generate career path suggestions
            career_paths = await self.ai_service.suggest_career_paths(
                cv_text=career_advice.cv_text,
                skills=career_advice.skills,
                interests=career_advice.interests
            )
            career_advice.career_paths = career_paths

            # Mark as processed
            career_advice.is_processed = True
            career_advice.processing_error = None

            await db.commit()
            await db.refresh(career_advice)

            # Cache the results
            cache_key = f"cv_analysis:{career_advice_id}"
            await redis.set(
                cache_key,
                career_advice.model_dump_json(),
                ex=settings.CACHE_EXPIRE_TIME
            )

        except Exception as e:
            if career_advice:
                career_advice.is_processed = True
                career_advice.processing_error = str(e)
                await db.commit()
            raise

    async def get_cv_analysis(
        self,
        db: AsyncSession,
        career_advice_id: UUID
    ) -> Optional[CareerAdvice]:
        """Get CV analysis by ID"""
        stmt = select(CareerAdvice).where(CareerAdvice.id == career_advice_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_advice_history(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[CareerAdvice]:
        """Get user's career advice history"""
        stmt = select(CareerAdvice).where(
            CareerAdvice.user_id == user_id
        ).order_by(CareerAdvice.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_cv_analysis(
        self,
        db: AsyncSession,
        career_advice_id: UUID
    ) -> bool:
        """Delete a CV analysis record"""
        stmt = select(CareerAdvice).where(CareerAdvice.id == career_advice_id)
        result = await db.execute(stmt)
        career_advice = result.scalar_one_or_none()

        if not career_advice:
            return False

        await db.delete(career_advice)
        await db.commit()
        return True

    async def cleanup_old_analyses(
        self,
        db: AsyncSession,
        days: int = 30
    ):
        """Cleanup old CV analyses"""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = select(CareerAdvice).where(CareerAdvice.created_at < cutoff_date)
        result = await db.execute(stmt)
        old_analyses = result.scalars().all()

        for analysis in old_analyses:
            await db.delete(analysis)

        await db.commit()
