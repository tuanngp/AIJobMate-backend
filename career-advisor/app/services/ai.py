from typing import List, Dict, Any, Optional
from loguru import logger
import openai
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config.settings import settings
from app.schemas.career import JobPreferences, CareerAdviceResponse

class AIService:
    def __init__(self):
        """Initialize AI service with API keys and models"""
        openai.api_key = settings.OPENAI_API_KEY
        self.cv_analysis_model = settings.CV_ANALYSIS_MODEL
        self.career_advice_model = settings.CAREER_ADVICE_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_cv_embedding(self, cv_text: str) -> List[float]:
        """Generate embedding vector for CV text"""
        try:
            response = await openai.embeddings.create(
                model=self.embedding_model,
                input=cv_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating CV embedding: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def analyze_skills(self, cv_text: str) -> Dict[str, Any]:
        """Extract and analyze skills from CV"""
        try:
            response = await openai.chat.completions.create(
                model=self.cv_analysis_model,
                messages=[
                    {"role": "system", "content": """
                    You are a skilled CV analyzer. Extract and categorize skills and interests from the CV.
                    Focus on both technical and soft skills. Group them logically.
                    """},
                    {"role": "user", "content": cv_text}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            # Parse and structure the response
            analysis = response.choices[0].message.content
            return {
                "skills": analysis.get("technical_skills", []) + analysis.get("soft_skills", []),
                "interests": analysis.get("interests", []),
                "skill_categories": analysis.get("skill_categories", {}),
                "proficiency_levels": analysis.get("proficiency_levels", {})
            }
        except Exception as e:
            logger.error(f"Error analyzing skills: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def analyze_cv(self, cv_text: str) -> Dict[str, Any]:
        """Analyze CV for strengths, weaknesses, and improvement areas"""
        try:
            response = await openai.chat.completions.create(
                model=self.cv_analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Analyze the CV to identify:
                    1. Key strengths and achievements
                    2. Potential weaknesses or gaps
                    3. Areas for improvement with actionable recommendations
                    4. Career progression patterns
                    Provide structured, actionable feedback.
                    """},
                    {"role": "user", "content": cv_text}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            analysis = response.choices[0].message.content
            return {
                "strengths": analysis.get("strengths", []),
                "weaknesses": analysis.get("weaknesses", []),
                "improvement_areas": analysis.get("improvement_areas", {}),
                "career_progression": analysis.get("career_progression", {})
            }
        except Exception as e:
            logger.error(f"Error analyzing CV: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def suggest_career_paths(
        self,
        cv_text: str,
        skills: List[str],
        interests: List[str]
    ) -> Dict[str, Any]:
        """Generate career path suggestions based on CV, skills, and interests"""
        try:
            # Combine all information for context
            context = f"""
            CV Content: {cv_text}
            
            Identified Skills: {', '.join(skills)}
            
            Interests: {', '.join(interests)}
            """

            response = await openai.chat.completions.create(
                model=self.career_advice_model,
                messages=[
                    {"role": "system", "content": """
                    Based on the CV content, skills, and interests, suggest potential career paths.
                    For each path include:
                    1. Role title and description
                    2. Required skills and qualifications
                    3. Growth potential
                    4. Industry trends
                    5. Estimated salary range
                    Provide practical, market-relevant suggestions.
                    """},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            suggestions = response.choices[0].message.content
            return {
                "career_paths": suggestions.get("career_paths", []),
                "market_insights": suggestions.get("market_insights", {}),
                "skill_gaps": suggestions.get("skill_gaps", {})
            }
        except Exception as e:
            logger.error(f"Error suggesting career paths: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_career_advice(
        self,
        cv_analysis: Any,
        preferences: JobPreferences,
        additional_context: Optional[str] = None
    ) -> CareerAdviceResponse:
        """Generate personalized career advice based on CV analysis and preferences"""
        try:
            # Combine all information for context
            context = f"""
            CV Analysis:
            - Skills: {', '.join(cv_analysis.skills)}
            - Strengths: {', '.join(cv_analysis.strengths)}
            - Weaknesses: {', '.join(cv_analysis.weaknesses)}
            
            Job Preferences:
            - Desired Role: {preferences.desired_role}
            - Industry: {preferences.desired_industry or 'Not specified'}
            - Experience Level: {preferences.experience_level or 'Not specified'}
            - Location: {preferences.location_preference or 'Not specified'}
            - Remote Preference: {preferences.remote_preference or 'Not specified'}
            
            Additional Context: {additional_context or 'None provided'}
            """

            response = await openai.chat.completions.create(
                model=self.career_advice_model,
                messages=[
                    {"role": "system", "content": """
                    You are a career advisor providing personalized advice based on:
                    1. CV analysis results
                    2. Individual job preferences
                    3. Market conditions and industry trends
                    
                    Provide specific, actionable advice including:
                    1. Career path recommendations
                    2. Skill development suggestions
                    3. Job search strategies
                    4. Industry-specific insights
                    """},
                    {"role": "user", "content": context}
                ],
                temperature=0.5,
                response_format={ "type": "json_object" }
            )
            
            advice = response.choices[0].message.content
            return CareerAdviceResponse(
                advice=advice.get("general_advice", ""),
                career_paths=advice.get("recommended_paths", []),
                skills_gap=advice.get("skills_gap", {}),
                next_steps=advice.get("next_steps", []),
                resources=advice.get("resources", [])
            )
        except Exception as e:
            logger.error(f"Error generating career advice: {str(e)}")
            raise
