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
    cv = None
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
        
        if analysis_result.get("error"):
            logger.error(f"CV {cv_id}: Lỗi từ CVProcessor: {analysis_result['error_message']}")
            raise ValueError(analysis_result["error_message"])
            
        # Cập nhật thông tin cơ bản
        basic_analysis = analysis_result.get("basic_analysis", {})
        cv.skills = basic_analysis.get("skills")
        cv.experiences = basic_analysis.get("experience", [])
        logger.info(f"CV {cv_id}: Tìm thấy {len(cv.experiences)} kinh nghiệm làm việc")
        cv.education = basic_analysis.get("education", [])
        
        # Cập nhật phân tích career
        career_analysis = analysis_result.get("career_analysis", {})
        cv.strengths = career_analysis.get("strengths", [])
        cv.weaknesses = career_analysis.get("weaknesses", [])
        cv.career_goals = career_analysis.get("career_paths", [])
        
        # Cập nhật career matches và related data
        career_matches = analysis_result.get("career_matches", [])
        cv.recommended_career_paths = career_matches
        cv.preferred_industries = list(set([
            match.get("industry", "").strip()
            for match in career_matches
            if match.get("industry")
        ]))
        
        # Cập nhật skill gaps và recommendations
        cv.skill_gaps = analysis_result.get("skill_gaps", [])
        cv.recommended_skills = [
            {"skill": gap.get("skill"), "importance": gap.get("importance")}
            for gap in analysis_result.get("skill_gaps", [])
            if isinstance(gap, dict) and gap.get("skill")
        ]
        cv.recommended_actions = career_analysis.get("recommended_actions", [])
        
        # Lưu vector embedding
        cv.embedding_vector = analysis_result.get("embedding_vector")
        
        # Cập nhật trạng thái và thời gian
        cv.analysis_status = "completed"
        cv.last_analyzed_at = datetime.utcnow()
        
        logger.info(f"CV {cv_id}: Lưu kết quả vào database")
        try:
            db.commit()
            logger.info(f"CV {cv_id}: Đã lưu thành công vào database")
        except Exception as db_error:
            logger.error(f"Database error while saving CV analysis: {str(db_error)}")
            raise
            
    except Exception as e:
        error_msg = f"Lỗi khi phân tích CV {cv_id}: {str(e)}"
        logger.error(f"CV {cv_id}: {error_msg}")
        logger.error(f"CV {cv_id}: Stacktrace:", exc_info=True)
        
        if cv:
            logger.info(f"CV {cv_id}: Cập nhật trạng thái lỗi")
            try:
                cv.analysis_status = "failed"
                cv.analysis_error = error_msg
                db.commit()
                logger.info(f"CV {cv_id}: Đã lưu trạng thái lỗi")
            except Exception as db_error:
                logger.error(f"Failed to update error status: {str(db_error)}")

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

@router.get("/{cv_id}/analyze", response_model=Dict[str, Any])
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
        
    response = {
        "status": cv.analysis_status,
        "basic_analysis": {
            "skills": cv.skills,
            "experiences": cv.experiences,
            "education": cv.education
        },
        "career_analysis": {
            "strengths": cv.strengths,
            "weaknesses": cv.weaknesses,
            "career_paths": cv.career_goals,
            "recommended_careers": cv.recommended_career_paths,
            "skill_gaps": cv.skill_gaps,
            "recommended_skills": cv.recommended_skills,
            "recommended_actions": cv.recommended_actions
        },
        "analysis_status": cv.analysis_status,
        "last_analyzed_at": cv.last_analyzed_at
    }
    
    if cv.analysis_status == "failed":
        response["error"] = cv.analysis_error
        
    return response

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