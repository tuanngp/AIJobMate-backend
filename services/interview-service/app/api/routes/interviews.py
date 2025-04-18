import json
import logging
from typing import Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Form
from sqlalchemy.orm import Session
from fastapi import APIRouter, UploadFile, File, Depends

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.schemas.interview import (
    Interview as InterviewSchema,
    InterviewCreate,
    InterviewUpdate,
    InterviewQuestion as InterviewQuestionSchema,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
)
from app.services.openai_service import generate_interview_questions, analyze_interview_answer, transcribe_audio
from app.services.redis_service import RedisService


# Cấu hình logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate", response_model=GenerateQuestionsResponse)
async def generate_questions(
    *,
    db: Session = Depends(get_db),
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Tạo câu hỏi phỏng vấn dựa trên các tiêu chí đầu vào sử dụng AI.
    """
    try:
        # Tạo một interview mới
        title = f"Phỏng vấn cho vị trí {request.job_title}"
        new_interview = Interview(
            user_id=current_user.id,
            title=title,
            job_title=request.job_title,
            job_description=request.job_description,
            industry=request.industry,
            difficulty_level=request.difficulty_level,
            interview_type=request.interview_type,
            status="draft"
        )
        
        db.add(new_interview)
        db.commit()
        db.refresh(new_interview)
        
        # Kiểm tra cache
        redis_service = RedisService.get_instance()
        cache_key = redis_service.generate_cache_key(
            "interview_questions",
            request.job_title,
            request.difficulty_level,
            request.interview_type,
            # Thêm các key khác nếu cần
        )
        
        questions_data = None
        try:
            questions_data = redis_service.get_cache(cache_key)
        except Exception as redis_error:
            logger.warning(f"Không thể lấy dữ liệu từ Redis, tiếp tục mà không dùng cache: {str(redis_error)}")
        
        # Nếu không có trong cache, gọi AI để tạo câu hỏi
        if not questions_data:
            try:
                questions_data = await generate_interview_questions(
                    job_title=request.job_title,
                    job_description=request.job_description,
                    industry=request.industry,
                    num_questions=request.num_questions,
                    difficulty_level=request.difficulty_level,
                    interview_type=request.interview_type,
                    skills_required=request.skills_required
                )
                
                # Lưu vào cache nếu Redis khả dụng
                try:
                    redis_service.set_cache(cache_key, questions_data, expiry=86400)  # Cache 24h
                except Exception as cache_error:
                    logger.warning(f"Không thể lưu dữ liệu vào Redis: {str(cache_error)}")
            except Exception as ai_error:
                logger.error(f"Lỗi khi gọi AI để tạo câu hỏi: {str(ai_error)}")
                # Trả về mẫu câu hỏi khi không thể kết nối đến API
                questions_data = [
                    {
                        "question": "Hãy giới thiệu về bản thân bạn và kinh nghiệm làm việc của bạn.",
                        "question_type": "behavioral",
                        "difficulty": "easy",
                        "category": "introduction",
                        "sample_answer": "Tôi là [tên], có X năm kinh nghiệm làm việc trong lĩnh vực Y. Tôi có kỹ năng Z và đã từng làm việc tại công ty A, B."
                    },
                    {
                        "question": f"Tại sao bạn quan tâm đến vị trí {request.job_title} tại công ty chúng tôi?",
                        "question_type": "behavioral",
                        "difficulty": "medium",
                        "category": "motivation",
                        "sample_answer": "Tôi quan tâm đến vị trí này vì có thể áp dụng kỹ năng X của mình. Tôi đã nghiên cứu về công ty và ấn tượng với [đặc điểm của công ty]."
                    }
                ]
        
        # Lưu câu hỏi vào database
        question_objects = []
        for q_data in questions_data:
            question = InterviewQuestion(
                interview_id=new_interview.id,
                question=q_data["question"],
                question_type=q_data["question_type"],
                difficulty=q_data["difficulty"],
                category=q_data.get("category"),
                sample_answer=q_data.get("sample_answer")
            )
            db.add(question)
            question_objects.append(question)
        
        db.commit()
        for q in question_objects:
            db.refresh(q)
        
        # Tạo response
        return {
            "interview_id": new_interview.id,
            "title": new_interview.title,
            "job_title": new_interview.job_title,
            "questions": question_objects
        }
    
    except Exception as e:
        # Rollback trong trường hợp lỗi
        db.rollback()
        logger.error(f"Lỗi khi tạo câu hỏi phỏng vấn: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo câu hỏi phỏng vấn: {str(e)}")

@router.get("/{interview_id}", response_model=InterviewSchema)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Lấy thông tin chi tiết của một phỏng vấn.
    """
    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy phỏng vấn")
    
    return interview

@router.get("/", response_model=List[InterviewSchema])
def get_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Lấy danh sách các phỏng vấn của người dùng.
    """
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return interviews

@router.post("/{interview_id}/questions/{question_id}/analyze")
async def analyze_answer(
    interview_id: int,
    question_id: int,
    user_answer: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Phân tích câu trả lời của người dùng đối với một câu hỏi phỏng vấn.
    """
    # Kiểm tra phỏng vấn
    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy phỏng vấn")
    
    # Kiểm tra câu hỏi
    question = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.id == question_id, InterviewQuestion.interview_id == interview_id)
        .first()
    )
    
    if not question:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    
    try:
        # Lưu câu trả lời của người dùng
        question.user_answer = user_answer
        
        # Phân tích câu trả lời bằng AI
        feedback = await analyze_interview_answer(
            question=question.question,
            question_type=question.question_type,
            user_answer=user_answer,
            job_title=interview.job_title
        )
        
        # Lưu phản hồi AI
        question.ai_feedback = json.dumps(feedback, ensure_ascii=False)
        
        db.add(question)
        db.commit()
        db.refresh(question)
        
        return {
            "question_id": question.id,
            "feedback": feedback
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi phân tích câu trả lời: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi phân tích câu trả lời: {str(e)}")

@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Xóa một phỏng vấn.
    """
    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id)
        .first()
    )
    
    if not interview:
        raise HTTPException(status_code=404, detail="Không tìm thấy phỏng vấn")
    
    db.delete(interview)
    db.commit()
    
    return {"message": "Đã xóa phỏng vấn thành công"} 


@router.post("/speech-to-text")
async def convert_speech_to_text(
    file: UploadFile = File(...),  # File âm thanh được tải lên
    current_user: User = Depends(get_current_user)  # Lấy thông tin người dùng
):
    """
    Nhận diện giọng nói từ file âm thanh và chuyển thành văn bản.
    Ngôn ngữ sẽ được tự động nhận diện từ file âm thanh.
    """
    try:
        text = await transcribe_audio(file)  # Hàm sẽ tự động nhận diện ngôn ngữ và chuyển thành text
        return {"transcript": text}  # Trả về văn bản
    except Exception as e:
        return {"error": str(e)}  # Trả về lỗi nếu có