from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from loguru import logger
import openai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config.settings import settings
from app.schemas.job import Job, SkillGapAnalysis, MarketAnalysis, SalaryRange

class AIService:
    def __init__(self):
        """Initialize AI models and embeddings"""
        openai.api_key = settings.OPENAI_API_KEY
        self.embedding_model = settings.EMBEDDING_MODEL
        self.analysis_model = settings.ANALYSIS_MODEL
        
        # Load BERT model for embeddings if not using OpenAI
        if settings.USE_LOCAL_EMBEDDINGS:
            self.bert_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            if settings.USE_GPU:
                self.bert_model.to('cuda')
            
        # Load skill taxonomy
        self.skill_taxonomy = self._load_skill_taxonomy()

    def _load_skill_taxonomy(self) -> Dict[str, Any]:
        """Load skill taxonomy from file"""
        try:
            import json
            with open(settings.SKILLS_DATA_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading skill taxonomy: {str(e)}")
            return {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_job_embedding(self, job: Job) -> List[float]:
        """Generate embedding vector for job description"""
        try:
            # Prepare job text
            job_text = f"""
            Title: {job.title}
            Company: {job.company}
            Description: {job.description}
            Requirements: {job.requirements}
            Skills: {', '.join(job.required_skills + job.preferred_skills)}
            """

            if settings.USE_LOCAL_EMBEDDINGS:
                # Use local BERT model
                embedding = self.bert_model.encode([job_text])[0]
            else:
                # Use OpenAI embeddings
                response = await openai.embeddings.create(
                    model=self.embedding_model,
                    input=job_text
                )
                embedding = response.data[0].embedding

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Error generating job embedding: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def extract_skills(self, text: str) -> Dict[str, Any]:
        """Extract skills from text using AI"""
        try:
            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Extract and categorize skills from the text. Include:
                    1. Technical skills
                    2. Soft skills
                    3. Domain knowledge
                    4. Tools and technologies
                    5. Certifications
                    
                    For each skill, provide:
                    - Category
                    - Required level (if mentioned)
                    - Years of experience (if mentioned)
                    - Is required or preferred
                    """},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            skills = response.choices[0].message.content
            
            # Validate against skill taxonomy
            validated_skills = self._validate_skills(skills)
            
            return validated_skills

        except Exception as e:
            logger.error(f"Error extracting skills: {str(e)}")
            raise

    def _validate_skills(self, extracted_skills: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize extracted skills against taxonomy"""
        validated = {
            "technical_skills": [],
            "soft_skills": [],
            "domain_knowledge": [],
            "tools": [],
            "certifications": []
        }

        for category, skills in extracted_skills.items():
            for skill in skills:
                # Check if skill exists in taxonomy
                normalized_skill = self._normalize_skill(skill["name"])
                if normalized_skill in self.skill_taxonomy:
                    skill["name"] = normalized_skill
                    skill["validated"] = True
                    skill["taxonomy_data"] = self.skill_taxonomy[normalized_skill]
                else:
                    skill["validated"] = False
                
                validated[category].append(skill)

        return validated

    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name for matching"""
        skill = skill.lower().strip()
        
        # Check aliases in taxonomy
        for tax_skill, data in self.skill_taxonomy.items():
            if skill in data.get("aliases", []):
                return tax_skill
                
        return skill

    async def analyze_skill_gaps(
        self,
        required_skills: List[str],
        user_skills: List[str],
        job_category: str
    ) -> SkillGapAnalysis:
        """Analyze skill gaps between required and user skills"""
        try:
            # Get skills data
            required_data = {
                skill: self.skill_taxonomy.get(self._normalize_skill(skill), {})
                for skill in required_skills
            }
            user_data = {
                skill: self.skill_taxonomy.get(self._normalize_skill(skill), {})
                for skill in user_skills
            }

            # Identify missing skills
            missing_critical = [
                skill for skill in required_skills 
                if skill not in user_skills
            ]
            
            # Calculate proficiency gaps
            proficiency_gaps = {}
            for skill in required_skills:
                if skill in user_skills:
                    req_level = required_data[skill].get("required_level", 1)
                    user_level = user_data[skill].get("level", 0)
                    gap = max(0, req_level - user_level)
                    if gap > 0:
                        proficiency_gaps[skill] = gap

            # Generate learning paths
            learning_paths = await self._generate_learning_paths(
                missing_critical,
                proficiency_gaps,
                job_category
            )

            # Estimate time to acquire
            time_estimates = {}
            for skill in missing_critical:
                if skill in self.skill_taxonomy:
                    time_estimates[skill] = self.skill_taxonomy[skill].get(
                        "estimated_learning_time",
                        "3-6 months"
                    )

            return SkillGapAnalysis(
                missing_critical_skills=missing_critical,
                missing_preferred_skills=[],  # TODO: Implement preferred skills
                skill_proficiency_gaps=proficiency_gaps,
                recommended_learning_paths=learning_paths,
                estimated_time_to_acquire=time_estimates
            )

        except Exception as e:
            logger.error(f"Error analyzing skill gaps: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def _generate_learning_paths(
        self,
        missing_skills: List[str],
        proficiency_gaps: Dict[str, float],
        job_category: str
    ) -> List[Dict[str, Any]]:
        """Generate personalized learning paths for missing skills"""
        try:
            context = {
                "missing_skills": missing_skills,
                "proficiency_gaps": proficiency_gaps,
                "job_category": job_category,
                "skill_taxonomy": self.skill_taxonomy
            }

            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Generate personalized learning paths for the missing skills.
                    For each skill include:
                    1. Prerequisites
                    2. Learning resources (online courses, books, etc.)
                    3. Practice projects
                    4. Estimated timeline
                    5. Key milestones
                    Order skills by priority and dependencies.
                    """},
                    {"role": "user", "content": str(context)}
                ],
                temperature=0.5,
                response_format={ "type": "json_object" }
            )
            
            learning_paths = response.choices[0].message.content
            return learning_paths.get("learning_paths", [])

        except Exception as e:
            logger.error(f"Error generating learning paths: {str(e)}")
            return []

    async def analyze_market_trends(
        self,
        job_category: str,
        skills: List[str],
        location: str
    ) -> MarketAnalysis:
        """Analyze job market trends for given category and skills"""
        try:
            # Get historical data and trends
            # This should be replaced with actual market data analysis
            trends = {
                "demand_level": "high",
                "growth_rate": 0.15,
                "salary_range": {
                    "min": 80000,
                    "max": 150000,
                    "currency": "USD",
                    "period": "yearly"
                },
                "top_employers": [
                    "Google",
                    "Microsoft",
                    "Amazon",
                    "Meta",
                    "Apple"
                ],
                "required_skills_frequency": {
                    skill: 0.8 for skill in skills
                },
                "location_opportunities": {
                    location: 500
                }
            }

            return MarketAnalysis(
                demand_level=trends["demand_level"],
                growth_rate=trends["growth_rate"],
                salary_range=SalaryRange(**trends["salary_range"]),
                top_employers=trends["top_employers"],
                required_skills_frequency=trends["required_skills_frequency"],
                location_opportunities=trends["location_opportunities"]
            )

        except Exception as e:
            logger.error(f"Error analyzing market trends: {str(e)}")
            raise

    def calculate_skill_match(
        self,
        required_skills: List[str],
        user_skills: List[str]
    ) -> float:
        """Calculate skill match score"""
        try:
            if not required_skills:
                return 0.0

            # Normalize skills
            required = set(self._normalize_skill(s) for s in required_skills)
            user = set(self._normalize_skill(s) for s in user_skills)

            # Calculate direct matches
            direct_matches = required.intersection(user)
            direct_score = len(direct_matches) / len(required)

            # Calculate semantic similarity for non-direct matches
            remaining_required = required - direct_matches
            remaining_user = user - direct_matches
            
            if remaining_required and remaining_user:
                # Get embeddings
                required_embeddings = [
                    self.skill_taxonomy[skill].get("embedding", [])
                    for skill in remaining_required
                    if skill in self.skill_taxonomy
                ]
                user_embeddings = [
                    self.skill_taxonomy[skill].get("embedding", [])
                    for skill in remaining_user
                    if skill in self.skill_taxonomy
                ]

                if required_embeddings and user_embeddings:
                    # Calculate similarity matrix
                    similarities = cosine_similarity(
                        required_embeddings,
                        user_embeddings
                    )
                    # Get best matches
                    semantic_score = np.mean(np.max(similarities, axis=1))
                else:
                    semantic_score = 0.0
            else:
                semantic_score = 0.0

            # Combine scores (70% direct matches, 30% semantic matches)
            final_score = (direct_score * 0.7) + (semantic_score * 0.3)
            return min(1.0, final_score)

        except Exception as e:
            logger.error(f"Error calculating skill match: {str(e)}")
            return 0.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_job_recommendations(
        self,
        user_profile: Dict[str, Any],
        available_jobs: List[Job]
    ) -> List[Dict[str, Any]]:
        """Generate personalized job recommendations"""
        try:
            # Calculate match scores
            matches = []
            for job in available_jobs:
                skill_match = self.calculate_skill_match(
                    job.required_skills,
                    user_profile.get("skills", [])
                )

                if skill_match >= settings.MATCH_THRESHOLD:
                    matches.append({
                        "job": job,
                        "skill_match": skill_match,
                        "match_factors": {
                            "skills": skill_match,
                            "experience": 0.8,  # TODO: Calculate actual score
                            "location": 0.9,  # TODO: Calculate actual score
                        }
                    })

            # Sort by overall match score
            matches.sort(key=lambda x: sum(x["match_factors"].values()), reverse=True)

            # Get detailed recommendations for top matches
            recommendations = []
            for match in matches[:settings.MAX_MATCHES]:
                recommendation = await self._generate_match_details(
                    match["job"],
                    user_profile,
                    match["match_factors"]
                )
                recommendations.append(recommendation)

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def _generate_match_details(
        self,
        job: Job,
        user_profile: Dict[str, Any],
        match_factors: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate detailed match analysis and recommendations"""
        try:
            context = {
                "job": job.model_dump(),
                "user_profile": user_profile,
                "match_factors": match_factors
            }

            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Analyze the job match and provide:
                    1. Key reasons for the match
                    2. Career growth potential
                    3. Specific recommendations for application
                    4. Tips for highlighting relevant experience
                    5. Preparation suggestions
                    """},
                    {"role": "user", "content": str(context)}
                ],
                temperature=0.5,
                response_format={ "type": "json_object" }
            )
            
            details = response.choices[0].message.content
            return details

        except Exception as e:
            logger.error(f"Error generating match details: {str(e)}")
            return {}
