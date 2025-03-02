from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime
import numpy as np
import librosa
import soundfile as sf
from loguru import logger
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config.settings import settings
from app.schemas.interview import (
    AudioMetadata,
    SpeechMetrics,
    SentimentAnalysis,
    ContentAnalysis,
    PerformanceMetrics
)

class AIService:
    def __init__(self):
        """Initialize AI service"""
        openai.api_key = settings.OPENAI_API_KEY
        self.speech_to_text_model = settings.SPEECH_TO_TEXT_MODEL
        self.analysis_model = settings.ANALYSIS_MODEL

    async def process_audio(
        self,
        audio_path: str,
        original_filename: str
    ) -> Tuple[AudioMetadata, np.ndarray]:
        """Process audio file and return metadata and numpy array"""
        try:
            # Load audio file
            audio, sr = librosa.load(audio_path, sr=settings.SAMPLE_RATE)
            
            # Get duration
            duration = librosa.get_duration(y=audio, sr=sr)
            
            # Get file format
            file_format = original_filename.split('.')[-1].lower()
            
            # Create metadata
            metadata = AudioMetadata(
                duration=duration,
                file_format=file_format,
                sample_rate=sr
            )
            
            return metadata, audio
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def transcribe_audio(self, audio_path: str) -> str:
        """Convert speech to text using Whisper"""
        try:
            with open(audio_path, "rb") as audio_file:
                response = await openai.audio.transcriptions.create(
                    model=self.speech_to_text_model,
                    file=audio_file,
                    response_format="text"
                )
            return response
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise

    async def analyze_speech_metrics(
        self,
        audio: np.ndarray,
        sr: int
    ) -> SpeechMetrics:
        """Analyze speech metrics (pace, clarity, filler words, etc.)"""
        try:
            # Calculate speech rate (words per minute)
            # Assuming average word length is ~5 frames at 100ms per frame
            frame_length = int(sr * 0.1)
            hop_length = int(sr * 0.05)
            rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)
            speech_frames = rms > rms.mean()
            word_count = speech_frames.sum() / 5
            duration_minutes = len(audio) / sr / 60
            pace = word_count / duration_minutes

            # Detect pauses
            pauses = []
            pause_threshold = 0.5
            is_pause = False
            pause_start = 0
            
            for i, power in enumerate(rms[0]):
                if power < rms.mean() * 0.5:
                    if not is_pause:
                        pause_start = i * hop_length / sr
                        is_pause = True
                elif is_pause:
                    pause_duration = (i * hop_length / sr) - pause_start
                    if pause_duration > pause_threshold:
                        pauses.append({"start": pause_start, "duration": pause_duration})
                    is_pause = False

            # Calculate clarity score based on signal-to-noise ratio
            snr = np.mean(rms) / np.std(rms)
            clarity_score = min(100, max(0, snr * 20))  # Scale to 0-100

            return SpeechMetrics(
                pace=pace,
                clarity=clarity_score,
                filler_words_count=0,  # Will be updated by content analysis
                filler_words=[],
                pauses=pauses,
                tone_variations={}  # Will be updated by sentiment analysis
            )
        except Exception as e:
            logger.error(f"Error analyzing speech metrics: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def analyze_sentiment(
        self,
        transcript: str,
        speech_metrics: SpeechMetrics
    ) -> SentimentAnalysis:
        """Analyze sentiment and emotions in the interview"""
        try:
            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Analyze the interview transcript for:
                    1. Confidence level
                    2. Enthusiasm
                    3. Stress level
                    4. Emotional states
                    Provide numerical scores (0-1) and detailed analysis.
                    """},
                    {"role": "user", "content": transcript}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            analysis = response.choices[0].message.content
            
            # Update speech metrics with tone variations
            speech_metrics.tone_variations = analysis.get("tone_variations", {})
            
            return SentimentAnalysis(
                confidence=analysis.get("confidence", 0.0),
                enthusiasm=analysis.get("enthusiasm", 0.0),
                stress_level=analysis.get("stress_level", 0.0),
                emotions=analysis.get("emotions", {})
            )
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def analyze_content(
        self,
        transcript: str,
        interview_type: str,
        job_role: str
    ) -> ContentAnalysis:
        """Analyze interview content and responses"""
        try:
            context = f"""
            Interview Type: {interview_type}
            Job Role: {job_role}
            Transcript: {transcript}
            """

            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Analyze the interview response for:
                    1. Relevance to questions
                    2. Completeness of answers
                    3. Structure and organization
                    4. Key points made
                    5. Important points missed
                    6. Technical accuracy (if applicable)
                    Provide detailed analysis with scores and explanations.
                    """},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            analysis = response.choices[0].message.content
            
            return ContentAnalysis(
                relevance=analysis.get("relevance", 0.0),
                completeness=analysis.get("completeness", 0.0),
                structure=analysis.get("structure", 0.0),
                key_points=analysis.get("key_points", []),
                missing_points=analysis.get("missing_points", []),
                technical_accuracy=analysis.get("technical_accuracy")
            )
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            raise

    def calculate_performance_metrics(
        self,
        speech_metrics: SpeechMetrics,
        sentiment_analysis: SentimentAnalysis,
        content_analysis: ContentAnalysis
    ) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        try:
            # Calculate clarity score (30% of total)
            clarity_score = speech_metrics.clarity * 0.3

            # Calculate content score (40% of total)
            content_score = (
                content_analysis.relevance * 0.4 +
                content_analysis.completeness * 0.4 +
                content_analysis.structure * 0.2
            ) * 40

            # Calculate confidence score (30% of total)
            confidence_score = (
                sentiment_analysis.confidence * 0.5 +
                sentiment_analysis.enthusiasm * 0.3 +
                (1 - sentiment_analysis.stress_level) * 0.2
            ) * 30

            # Calculate overall score
            overall_score = clarity_score + content_score + confidence_score

            return PerformanceMetrics(
                clarity_score=clarity_score,
                content_score=content_score,
                confidence_score=confidence_score,
                overall_score=overall_score
            )
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_feedback(
        self,
        speech_metrics: SpeechMetrics,
        sentiment_analysis: SentimentAnalysis,
        content_analysis: ContentAnalysis,
        performance_metrics: PerformanceMetrics
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate comprehensive feedback and recommendations"""
        try:
            context = {
                "speech_metrics": speech_metrics.model_dump(),
                "sentiment_analysis": sentiment_analysis.model_dump(),
                "content_analysis": content_analysis.model_dump(),
                "performance_metrics": performance_metrics.model_dump()
            }

            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Generate comprehensive interview feedback including:
                    1. Overall assessment
                    2. Specific strengths
                    3. Areas for improvement
                    4. Actionable recommendations
                    5. Practice suggestions
                    Provide constructive, specific, and actionable feedback.
                    """},
                    {"role": "user", "content": str(context)}
                ],
                temperature=0.5,
                response_format={ "type": "json_object" }
            )
            
            feedback = response.choices[0].message.content
            
            return (
                feedback.get("overall_feedback", ""),
                feedback.get("recommendations", []),
                feedback.get("practice_suggestions", {})
            )
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            raise
