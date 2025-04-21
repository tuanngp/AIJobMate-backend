from typing import Any, Dict, List
from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.practice_session import PracticeSession
from app.schemas.practice_session import (
    PracticeSessionCreate,
    PracticeSessionResponse,
    AnswerRecordingCreate,
    AnswerRecordingResponse
)
from app.services.session_service import SessionService
from app.services.storage_service import StorageService
from app.services.connection_manager import ConnectionManager
import logging

router = APIRouter()
session_service = SessionService()
storage_service = StorageService()
manager = ConnectionManager()
logger = logging.getLogger(__name__)

@router.post("", response_model=PracticeSessionResponse)
async def create_session(
    *,
    db: Session = Depends(get_db),
    data: PracticeSessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Tạo một phiên luyện tập mới"""
    return await session_service.create_session(db, current_user["id"], data)

@router.get("/{session_id}", response_model=PracticeSessionResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lấy thông tin chi tiết của một phiên luyện tập"""
    return await session_service.get_session(db, current_user["id"], session_id)

@router.post("/{session_id}/answers", response_model=AnswerRecordingResponse)
async def submit_answer(
    session_id: int,
    data: AnswerRecordingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit câu trả lời cho một câu hỏi trong phiên luyện tập"""
    return await session_service.submit_answer(
        db, 
        current_user["id"],
        session_id, 
        data,
        background_tasks
    )

@router.get("", response_model=List[PracticeSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lấy danh sách các phiên luyện tập của người dùng"""
    return await session_service.list_sessions(db, current_user["id"], skip, limit)

@router.websocket("/ws/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        # Verify token and get user
        current_user = get_current_user(db, token)
        
        # Verify session belongs to user
        session = db.query(PracticeSession).filter(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user["id"]
        ).first()
        if not session:
            await websocket.close(code=4004)
            return

        # Accept connection
        await websocket.accept()
        
        # Add to connection manager
        await manager.connect(websocket, session_id)
        
        try:
            while True:
                # Listen for messages
                data = await websocket.receive_json()
                
                # Handle different message types
                if data["type"] == "answer_submitted":
                    # Broadcast progress update
                    await manager.broadcast_to_session(
                        session_id,
                        {
                            "type": "progress_update",
                            "completed": session.completed_questions,
                            "total": session.total_questions
                        }
                    )
        except WebSocketDisconnect:
            await manager.disconnect(websocket, session_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=4000)