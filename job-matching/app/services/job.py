from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import asyncio
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import pandas as pd
from loguru import logger

from app.config.settings import settings
from app.models.job import Job, JobMatch, JobPreference, UserSkillProfile
from app.schemas.job import (
    JobCreate,
    JobSearchParams,
    JobSearchResponse,
    JobRecommendation,
    RecommendationResponse,
    SkillGapAnalysis,
    MarketAnalysis
)
from app.services.ai import AIService
from app.services.scraper import ScraperService

class JobService:
    def __init__(
        self,
        ai_service: AIService = AIService(),
        scraper_service: ScraperService = ScraperService()
    ):
        """Initialize job service"""
        self.ai_service = ai_service
        self.scraper_service = scraper_service

    async def create_job(
        self,
        job_data: JobCreate,
        db: AsyncSession
    ) -> Job:
        """Create a new job posting"""
        try:
            # Generate embeddings
            embedding = await self.ai_service.generate_job_embedding(job_data)
            
            # Extract skills
            extracted_skills = await self.ai_service.extract_skills(
                job_data.description + "\n" + job_data.requirements
            )

            # Create job
            job = Job(
                **job_data.model_dump(),
                embedding=embedding,
                extracted_skills=extracted_skills
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            return job

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating job: {str(e)}")
            raise

    async def search_jobs(
        self,
        params: JobSearchParams,
        db: AsyncSession
    ) -> JobSearchResponse:
        """Search for jobs with filters"""
        try:
            # Build base query
            query = select(Job).where(Job.is_active == True)

            # Apply filters
            if params.query:
                query = query.where(
                    or_(
                        Job.title.ilike(f"%{params.query}%"),
                        Job.description.ilike(f"%{params.query}%"),
                        Job.company.ilike(f"%{params.query}%")
                    )
                )

            if params.location:
                query = query.where(Job.location.ilike(f"%{params.location}%"))

            if params.remote_only:
                query = query.where(Job.remote_type != "no")

            if params.job_types:
                query = query.where(Job.job_type.in_(params.job_types))

            if params.experience_levels:
                query = query.where(Job.experience_level.in_(params.experience_levels))

            if params.industries:
                query = query.where(Job.industry.in_(params.industries))

            if params.min_salary:
                query = query.where(Job.salary_max >= params.min_salary)

            if params.posted_within_days:
                cutoff_date = datetime.utcnow() - pd.Timedelta(days=params.posted_within_days)
                query = query.where(Job.posted_at >= cutoff_date)

            if params.skills:
                # Search in required and preferred skills
                query = query.where(
                    or_(
                        Job.required_skills.overlap(params.skills),
                        Job.preferred_skills.overlap(params.skills)
                    )
                )

            if params.company_sizes:
                query = query.where(Job.company_size.in_(params.company_sizes))

            # Apply sorting
            if params.sort_by == "date":
                query = query.order_by(Job.posted_at.desc())
            elif params.sort_by == "salary":
                query = query.order_by(Job.salary_max.desc())
            else:  # relevance - based on matching score
                # TODO: Implement relevance sorting using embeddings
                pass

            # Get total count
            count_query = select(text("count(*)")).select_from(query)
            total = await db.scalar(count_query)

            # Apply pagination
            query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
            result = await db.execute(query)
            jobs = result.scalars().all()

            # Generate facets
            facets = await self._generate_search_facets(jobs)

            # Generate search suggestions
            suggestions = await self._generate_search_suggestions(params, jobs)

            return JobSearchResponse(
                total=total,
                page=params.page,
                page_size=params.page_size,
                results=jobs,
                facets=facets,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            raise

    async def get_job_recommendations(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> RecommendationResponse:
        """Get personalized job recommendations"""
        try:
            # Get user profile and preferences
            profile_query = select(UserSkillProfile).where(
                UserSkillProfile.user_id == user_id
            )
            pref_query = select(JobPreference).where(
                JobPreference.user_id == user_id
            )
            
            profile_result = await db.execute(profile_query)
            pref_result = await db.execute(pref_query)
            
            profile = profile_result.scalar_one_or_none()
            preferences = pref_result.scalar_one_or_none()

            if not profile:
                raise ValueError("User profile not found")

            # Get matching jobs
            matching_jobs = await self._find_matching_jobs(profile, preferences, db)

            # Generate recommendations
            recommendations = await self.ai_service.generate_job_recommendations(
                profile.model_dump(),
                matching_jobs
            )

            # Get market insights
            market_trends = await self._analyze_market_trends(profile, matching_jobs)

            # Generate skill suggestions
            skill_suggestions = await self._generate_skill_suggestions(
                profile.skills,
                [job.required_skills for job in matching_jobs]
            )

            # Generate career path suggestions
            career_paths = await self._suggest_career_paths(profile, matching_jobs)

            return RecommendationResponse(
                recommendations=[
                    JobRecommendation(
                        job=job["job"],
                        match_score=job["match_score"],
                        match_reasons=job["match_reasons"],
                        skill_match=job["skill_match"],
                        missing_skills=job["missing_skills"],
                        salary_comparison=job.get("salary_comparison"),
                        market_insights=job.get("market_insights", {})
                    )
                    for job in recommendations
                ],
                total_matches=len(matching_jobs),
                market_trends=market_trends,
                skill_suggestions=skill_suggestions,
                career_path_suggestions=career_paths
            )

        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            raise

    async def analyze_skill_gaps(
        self,
        job_id: UUID,
        user_id: UUID,
        db: AsyncSession
    ) -> SkillGapAnalysis:
        """Analyze skill gaps for a specific job"""
        try:
            # Get job and user profile
            job_query = select(Job).where(Job.id == job_id)
            profile_query = select(UserSkillProfile).where(
                UserSkillProfile.user_id == user_id
            )
            
            job_result = await db.execute(job_query)
            profile_result = await db.execute(profile_query)
            
            job = job_result.scalar_one_or_none()
            profile = profile_result.scalar_one_or_none()

            if not job or not profile:
                raise ValueError("Job or user profile not found")

            return await self.ai_service.analyze_skill_gaps(
                job.required_skills + job.preferred_skills,
                list(profile.skills.keys()),
                job.job_category
            )

        except Exception as e:
            logger.error(f"Error analyzing skill gaps: {str(e)}")
            raise

    async def get_market_analysis(
        self,
        job_category: str,
        skills: List[str],
        location: str,
        db: AsyncSession
    ) -> MarketAnalysis:
        """Get market analysis for given job category and skills"""
        try:
            return await self.ai_service.analyze_market_trends(
                job_category,
                skills,
                location
            )
        except Exception as e:
            logger.error(f"Error getting market analysis: {str(e)}")
            raise

    async def refresh_job_listings(self, db: AsyncSession) -> Dict[str, Any]:
        """Refresh job listings from various sources"""
        try:
            total_added = 0
            total_updated = 0
            errors = []

            for job_board in settings.SUPPORTED_JOB_BOARDS:
                try:
                    # Get jobs from each board
                    jobs = await self._scrape_and_process_jobs(job_board)
                    
                    for job_data in jobs:
                        try:
                            # Check if job already exists
                            existing = await self._find_existing_job(
                                job_data.source,
                                job_data.source_id,
                                db
                            )

                            if existing:
                                # Update existing job
                                await self._update_job(existing, job_data, db)
                                total_updated += 1
                            else:
                                # Create new job
                                await self.create_job(job_data, db)
                                total_added += 1

                        except Exception as e:
                            errors.append({
                                "job": job_data.title,
                                "source": job_board,
                                "error": str(e)
                            })

                except Exception as e:
                    errors.append({
                        "source": job_board,
                        "error": str(e)
                    })

            return {
                "added": total_added,
                "updated": total_updated,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error refreshing job listings: {str(e)}")
            raise

    async def _find_matching_jobs(
        self,
        profile: UserSkillProfile,
        preferences: Optional[JobPreference],
        db: AsyncSession
    ) -> List[Job]:
        """Find jobs matching user profile and preferences"""
        try:
            # Start with base query
            query = select(Job).where(Job.is_active == True)

            # Apply skill matching
            user_skills = list(profile.skills.keys())
            query = query.where(
                or_(
                    Job.required_skills.overlap(user_skills),
                    Job.preferred_skills.overlap(user_skills)
                )
            )

            # Apply preference filters if available
            if preferences:
                if preferences.desired_titles:
                    query = query.where(Job.normalized_title.in_(preferences.desired_titles))
                
                if preferences.desired_industries:
                    query = query.where(Job.industry.in_(preferences.desired_industries))
                
                if preferences.min_salary:
                    query = query.where(Job.salary_max >= preferences.min_salary)
                
                if preferences.locations:
                    location_filters = [
                        Job.location.ilike(f"%{loc}%") for loc in preferences.locations
                    ]
                    query = query.where(or_(*location_filters))
                
                if preferences.remote_preference == "remote":
                    query = query.where(Job.remote_type == "full")

            # Get results
            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error finding matching jobs: {str(e)}")
            raise

    async def _analyze_market_trends(
        self,
        profile: UserSkillProfile,
        matching_jobs: List[Job]
    ) -> Dict[str, Any]:
        """Analyze market trends from matching jobs"""
        try:
            # Calculate average salaries
            salaries = [
                (job.salary_min + job.salary_max) / 2
                for job in matching_jobs
                if job.salary_min and job.salary_max
            ]
            avg_salary = sum(salaries) / len(salaries) if salaries else 0

            # Get top companies
            companies = {}
            for job in matching_jobs:
                companies[job.company] = companies.get(job.company, 0) + 1
            top_companies = sorted(
                companies.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            # Analyze skill demand
            required_skills = {}
            for job in matching_jobs:
                for skill in job.required_skills:
                    required_skills[skill] = required_skills.get(skill, 0) + 1
            
            skill_demand = {
                skill: count / len(matching_jobs)
                for skill, count in required_skills.items()
            }

            return {
                "average_salary": avg_salary,
                "total_openings": len(matching_jobs),
                "top_companies": dict(top_companies),
                "skill_demand": skill_demand,
                "market_growth": 0.15,  # TODO: Calculate actual growth
                "competition_level": "medium"  # TODO: Calculate based on applications
            }

        except Exception as e:
            logger.error(f"Error analyzing market trends: {str(e)}")
            return {}

    async def _generate_skill_suggestions(
        self,
        user_skills: Dict[str, Any],
        job_skills_lists: List[List[str]]
    ) -> Dict[str, Any]:
        """Generate skill suggestions based on job requirements"""
        try:
            # Flatten and count all required skills
            all_required = {}
            for skills in job_skills_lists:
                for skill in skills:
                    all_required[skill] = all_required.get(skill, 0) + 1

            # Filter out skills user already has
            missing_skills = {
                skill: count
                for skill, count in all_required.items()
                if skill not in user_skills
            }

            # Sort by frequency
            sorted_skills = sorted(
                missing_skills.items(),
                key=lambda x: x[1],
                reverse=True
            )

            return {
                "recommended_skills": [s[0] for s in sorted_skills[:10]],
                "skill_demand": {s[0]: s[1] / len(job_skills_lists) for s in sorted_skills},
                "learning_resources": {}  # TODO: Add learning resources
            }

        except Exception as e:
            logger.error(f"Error generating skill suggestions: {str(e)}")
            return {}

    async def _suggest_career_paths(
        self,
        profile: UserSkillProfile,
        matching_jobs: List[Job]
    ) -> List[Dict[str, Any]]:
        """Generate career path suggestions"""
        try:
            # Group jobs by level/seniority
            jobs_by_level = {}
            for job in matching_jobs:
                level = self._extract_job_level(job.title)
                if level not in jobs_by_level:
                    jobs_by_level[level] = []
                jobs_by_level[level].append(job)

            # Generate career paths
            career_paths = []
            current_level = self._extract_experience_level(profile.work_history)

            for next_level in self._get_next_levels(current_level):
                if next_level in jobs_by_level:
                    path = {
                        "current_level": current_level,
                        "next_level": next_level,
                        "required_skills": self._extract_common_skills(
                            jobs_by_level[next_level]
                        ),
                        "typical_roles": self._extract_common_titles(
                            jobs_by_level[next_level]
                        ),
                        "salary_range": self._calculate_salary_range(
                            jobs_by_level[next_level]
                        ),
                        "time_to_achieve": self._estimate_time_to_achieve(
                            current_level,
                            next_level
                        )
                    }
                    career_paths.append(path)

            return career_paths

        except Exception as e:
            logger.error(f"Error suggesting career paths: {str(e)}")
            return []

    def _extract_job_level(self, title: str) -> str:
        """Extract job level from title"""
        title = title.lower()
        if "senior" in title or "sr" in title:
            return "senior"
        elif "lead" in title or "principal" in title:
            return "lead"
        elif "manager" in title:
            return "manager"
        elif "junior" in title or "jr" in title:
            return "junior"
        else:
            return "mid"

    def _extract_experience_level(self, work_history: List[Dict[str, Any]]) -> str:
        """Extract experience level from work history"""
        total_years = sum(
            job.get("duration_years", 0)
            for job in work_history
        )
        
        if total_years < 2:
            return "junior"
        elif total_years < 5:
            return "mid"
        elif total_years < 8:
            return "senior"
        else:
            return "lead"

    def _get_next_levels(self, current_level: str) -> List[str]:
        """Get possible next career levels"""
        levels = {
            "junior": ["mid"],
            "mid": ["senior"],
            "senior": ["lead", "manager"],
            "lead": ["manager"],
            "manager": ["director"]
        }
        return levels.get(current_level, [])

    def _extract_common_skills(self, jobs: List[Job]) -> List[str]:
        """Extract common required skills from jobs"""
        skill_count = {}
        for job in jobs:
            for skill in job.required_skills:
                skill_count[skill] = skill_count.get(skill, 0) + 1
        
        # Return skills required by at least 50% of jobs
        threshold = len(jobs) * 0.5
        return [
            skill for skill, count in skill_count.items()
            if count >= threshold
        ]

    def _extract_common_titles(self, jobs: List[Job]) -> List[str]:
        """Extract common job titles"""
        titles = {}
        for job in jobs:
            normalized = job.normalized_title or job.title
            titles[normalized] = titles.get(normalized, 0) + 1
        
        # Return top 5 most common titles
        sorted_titles = sorted(
            titles.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [title for title, _ in sorted_titles[:5]]

    def _calculate_salary_range(self, jobs: List[Job]) -> Dict[str, float]:
        """Calculate salary range for job group"""
        salaries_min = []
        salaries_max = []
        
        for job in jobs:
            if job.salary_min:
                salaries_min.append(job.salary_min)
            if job.salary_max:
                salaries_max.append(job.salary_max)

        return {
            "min": min(salaries_min) if salaries_min else 0,
            "max": max(salaries_max) if salaries_max else 0,
            "average": (
                sum(salaries_min) / len(salaries_min) if salaries_min else 0 +
                sum(salaries_max) / len(salaries_max) if salaries_max else 0
            ) / 2
        }

    def _estimate_time_to_achieve(
        self,
        current_level: str,
        next_level: str
    ) -> str:
        """Estimate time needed to reach next level"""
        estimates = {
            ("junior", "mid"): "1-2 years",
            ("mid", "senior"): "2-3 years",
            ("senior", "lead"): "2-3 years",
            ("senior", "manager"): "3-4 years",
            ("lead", "manager"): "1-2 years",
            ("manager", "director"): "3-5 years"
        }
        return estimates.get((current_level, next_level), "Unknown")

    async def _find_existing_job(
        self,
        source: str,
        source_id: str,
        db: AsyncSession
    ) -> Optional[Job]:
        """Find existing job by source and source_id"""
        query = select(Job).where(
            and_(
                Job.source == source,
                Job.source_id == source_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _update_job(
        self,
        existing: Job,
        new_data: JobCreate,
        db: AsyncSession
    ) -> Job:
        """Update existing job with new data"""
        try:
            # Update fields
            for field, value in new_data.model_dump().items():
                setattr(existing, field, value)

            # Update embedding and skills
            existing.embedding = await self.ai_service.generate_job_embedding(new_data)
            existing.extracted_skills = await self.ai_service.extract_skills(
                new_data.description + "\n" + new_data.requirements
            )

            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)

            return existing

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating job: {str(e)}")
            raise

    async def _generate_search_facets(self, jobs: List[Job]) -> Dict[str, Any]:
        """Generate search facets from job results"""
        try:
            facets = {
                "job_types": {},
                "experience_levels": {},
                "industries": {},
                "companies": {},
                "locations": {},
                "salary_ranges": {
                    "0-50k": 0,
                    "50k-100k": 0,
                    "100k-150k": 0,
                    "150k+": 0
                },
                "remote_types": {},
                "skills": {}
            }

            for job in jobs:
                # Count job types
                if job.job_type:
                    facets["job_types"][job.job_type] = \
                        facets["job_types"].get(job.job_type, 0) + 1

                # Count experience levels
                if job.experience_level:
                    facets["experience_levels"][job.experience_level] = \
                        facets["experience_levels"].get(job.experience_level, 0) + 1

                # Count industries
                if job.industry:
                    facets["industries"][job.industry] = \
                        facets["industries"].get(job.industry, 0) + 1

                # Count companies
                facets["companies"][job.company] = \
                    facets["companies"].get(job.company, 0) + 1

                # Count locations
                facets["locations"][job.location] = \
                    facets["locations"].get(job.location, 0) + 1

                # Count salary ranges
                if job.salary_max:
                    if job.salary_max < 50000:
                        facets["salary_ranges"]["0-50k"] += 1
                    elif job.salary_max < 100000:
                        facets["salary_ranges"]["50k-100k"] += 1
                    elif job.salary_max < 150000:
                        facets["salary_ranges"]["100k-150k"] += 1
                    else:
                        facets["salary_ranges"]["150k+"] += 1

                # Count remote types
                if job.remote_type:
                    facets["remote_types"][job.remote_type] = \
                        facets["remote_types"].get(job.remote_type, 0) + 1

                # Count skills
                for skill in job.required_skills:
                    facets["skills"][skill] = \
                        facets["skills"].get(skill, 0) + 1

            return facets

        except Exception as e:
            logger.error(f"Error generating search facets: {str(e)}")
            return {}

    async def _generate_search_suggestions(
        self,
        params: JobSearchParams,
        jobs: List[Job]
    ) -> Dict[str, Any]:
        """Generate search suggestions based on results"""
        try:
            suggestions = {
                "related_searches": [],
                "popular_companies": [],
                "trending_skills": [],
                "salary_insights": {}
            }

            if params.query:
                # Get related job titles
                titles = [job.title for job in jobs]
                suggestions["related_searches"] = self._find_similar_titles(
                    params.query,
                    titles
                )

            # Get top companies
            company_count = {}
            for job in jobs:
                company_count[job.company] = company_count.get(job.company, 0) + 1
            suggestions["popular_companies"] = [
                company for company, _ in sorted(
                    company_count.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ]

            # Get trending skills
            skill_count = {}
            for job in jobs:
                for skill in job.required_skills:
                    skill_count[skill] = skill_count.get(skill, 0) + 1
            suggestions["trending_skills"] = [
                skill for skill, _ in sorted(
                    skill_count.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ]

            # Calculate salary insights
            salaries = [
                (job.salary_min + job.salary_max) / 2
                for job in jobs
                if job.salary_min and job.salary_max
            ]
            if salaries:
                suggestions["salary_insights"] = {
                    "average": sum(salaries) / len(salaries),
                    "range": {
                        "min": min(salaries),
                        "max": max(salaries)
                    }
                }

            return suggestions

        except Exception as e:
            logger.error(f"Error generating search suggestions: {str(e)}")
            return {}

    def _find_similar_titles(self, query: str, titles: List[str]) -> List[str]:
        """Find similar job titles based on query"""
        try:
            # Simple word overlap similarity
            query_words = set(query.lower().split())
            similar = []
            
            for title in titles:
                title_words = set(title.lower().split())
                overlap = len(query_words & title_words)
                if overlap > 0:
                    similar.append((title, overlap))
            
            # Return top 5 most similar titles
            return [
                title for title, _ in sorted(
                    similar,
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ]

        except Exception as e:
            logger.error(f"Error finding similar titles: {str(e)}")
            return []
