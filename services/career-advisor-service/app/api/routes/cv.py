import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from app.api import deps
from app.models.user import User
from app.models.cv import CV
from app.schemas.cv import CVInDB, CVAnalysisResponse
from app.services.cv_processor import CVProcessor
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=CVInDB)
async def upload_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    file: UploadFile = File(...)
) -> CVInDB:
    """
    Upload và xử lý CV
    """
    try:
        # Xử lý file CV
        file_name, file_type, extracted_text = await CVProcessor.process_cv(file)
        
        # Lưu file content
        await file.seek(0)
        original_content = await file.read()
        
        # Xử lý content cho text file
        original_content_str = None
        if file_type == 'txt':
            original_content_str = original_content.decode('utf-8') if isinstance(original_content, bytes) else original_content
        
        # Tạo hoặc lấy user
        user_id = current_user.get("id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.flush()
        
        # Tạo CV record
        cv = CV(
            user_id=user.id,
            file_name=file_name,
            file_type=file_type,
            original_content=original_content_str,
            extracted_text=extracted_text,
            analysis_status="pending"
        )
        
        db.add(cv)
        db.commit()
        db.refresh(cv)
        
        return CVInDB.from_orm(cv)
            
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Đã xảy ra lỗi khi xử lý CV: {str(e)}"
        )

async def run_analysis(cv_id: int, db: Session):
    """
    Thực hiện phân tích CV trong background
    """
    try:
        cv = db.query(CV).filter(CV.id == cv_id).first()
        if not cv:
            logger.error(f"CV {cv_id} không tồn tại")
            return
        
        # Cập nhật trạng thái
        cv.analysis_status = "processing"
        cv.last_analyzed_at = datetime.utcnow()
        db.commit()
        
        # Phân tích CV
        analysis_result = await CVProcessor.analyze_cv(cv_id, cv.extracted_text)
        
        # Cập nhật kết quả vào CV
        cv.skills = analysis_result.get("cv_analysis", {}).get("skills")
        cv.experiences = analysis_result.get("cv_analysis", {}).get("experience")
        cv.education = analysis_result.get("cv_analysis", {}).get("education")
        cv.career_goals = analysis_result.get("career_analysis", {}).get("career_paths")
        cv.preferred_industries = [path.get("industry") for path in analysis_result.get("career_matches", [])]
        
        cv.strengths = analysis_result.get("career_analysis", {}).get("strengths")
        cv.weaknesses = analysis_result.get("career_analysis", {}).get("weaknesses")
        cv.skill_gaps = analysis_result.get("skill_gaps", {}).get("missing_skills")
        cv.recommended_career_paths = analysis_result.get("career_matches")
        cv.recommended_skills = analysis_result.get("skill_gaps", {}).get("recommended_skills")
        cv.recommended_actions = analysis_result.get("career_analysis", {}).get("recommended_actions")
        
        cv.embedding_vector = analysis_result.get("embedding_vector")
        cv.analysis_status = "completed"
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error analyzing CV {cv_id}: {str(e)}")
        if cv:
            cv.analysis_status = "failed"
            cv.analysis_error = str(e)
            db.commit()

@router.post("/{cv_id}/analyze", response_model=CVAnalysisResponse)
async def analyze_cv(
    *,
    cv_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Phân tích CV và cung cấp thông tin career
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.get("id")).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
    
    # Thêm task phân tích vào background
    background_tasks.add_task(run_analysis, cv_id, db)
    
    return {"status": "processing", "message": "Đang phân tích CV"}

@router.get("/{cv_id}/analysis", response_model=Dict[str, Any])
async def get_analysis(
    *,
    cv_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Lấy kết quả phân tích CV
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.get("id")).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")
        
    if cv.analysis_status == "failed":
        raise HTTPException(status_code=500, detail=cv.analysis_error or "Phân tích thất bại")
        
    if cv.analysis_status == "processing":
        return {"status": "processing", "message": "Đang phân tích CV"}
        
    return {
        "status": cv.analysis_status,
        "career_analysis": {
            "strengths": cv.strengths,
            "weaknesses": cv.weaknesses,
            "skill_gaps": cv.skill_gaps,
            "recommended_careers": cv.recommended_career_paths,
            "recommended_skills": cv.recommended_skills,
            "recommended_actions": cv.recommended_actions
        },
        "last_analyzed_at": cv.last_analyzed_at
    }

@router.get("/list", response_model=List[CVInDB])
def list_cvs(
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> List[CVInDB]:
    """
    Lấy danh sách CV của người dùng
    """
    return (
        db.query(CV)
        .filter(CV.user_id == current_user.get("id"))
        .order_by(CV.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@router.get("/{cv_id}", response_model=CVInDB)
def get_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    cv_id: int
) -> CVInDB:
    """
    Lấy thông tin chi tiết CV
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.get("id")).first()
    if not cv:
        raise HTTPException(
            status_code=404,
            detail="CV không tồn tại hoặc không thuộc về người dùng này"
        )
    return cv