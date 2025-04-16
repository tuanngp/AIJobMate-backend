from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.models.practice_session import PracticeSession, AnswerRecording
from app.models.interview import Interview
from app.schemas.practice_session import PracticeSessionCreate, AnswerRecordingCreate
from app.services.openai_service import analyze_interview_answer
from app.services.storage_service import StorageService

class SessionService:
    def __init__(self):
        self.storage = StorageService()

    async def create_session(
        self, 
        db: Session,
        user_id: int,
        data: PracticeSessionCreate
    ) -> PracticeSession:
        # Verify interview exists and belongs to user
        interview = db.query(Interview).filter(
            Interview.id == data.interview_id,
            Interview.user_id == user_id
        ).first()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        # Create new session
        session = PracticeSession(
            user_id=user_id,
            interview_id=data.interview_id,
            total_questions=len(interview.questions),
            settings=data.settings.dict() if data.settings else None
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    async def submit_answer(
        self,
        db: Session,
        user_id: int,
        session_id: int,
        data: AnswerRecordingCreate,
        background_tasks: BackgroundTasks
    ) -> AnswerRecording:
        # Verify session belongs to user
        session = db.query(PracticeSession).filter(
            PracticeSession.id == session_id,
            PracticeSession.user_id == user_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Create recording entry
        recording = AnswerRecording(
            session_id=session_id,
            question_id=data.question_id,
            audio_url=data.audio_url,
            transcription=data.transcription
        )
        db.add(recording)

        # Update session progress
        session.completed_questions += 1
        if session.completed_questions == session.total_questions:
            session.end_time = datetime.now()
            session.status = "completed"

        # Schedule background analysis
        background_tasks.add_task(
            self._analyze_answer,
            db,
            recording,
            session
        )

        db.commit()
        db.refresh(recording)
        return recording

    async def _analyze_answer(
        self,
        db: Session,
        recording: AnswerRecording,
        session: PracticeSession
    ):
        """Background task to analyze answer and update feedback"""
        try:
            # Get question details
            question = db.query(InterviewQuestion).get(recording.question_id)
            
            # Analyze answer
            feedback = await analyze_interview_answer(
                question=question.question,
                question_type=question.question_type,
                user_answer=recording.transcription,
                job_title=session.interview.job_title
            )

            # Update recording
            recording.feedback = feedback
            recording.score = feedback.get("overall_score", None)

            # Update session average score
            recordings = db.query(AnswerRecording).filter(
                AnswerRecording.session_id == session.id,
                AnswerRecording.score.isnot(None)
            ).all()
            
            if recordings:
                session.average_score = sum(r.score for r in recordings) / len(recordings)

            db.commit()

        except Exception as e:
            logger.error(f"Error analyzing answer: {str(e)}")
            # Don't raise exception - this is a background task