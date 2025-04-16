import asyncio
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from app.api import deps
from app.models.cv import CV
from app.schemas.cv import CVInDB, CVAnalysisResponse, ResumeAnalysisResponse
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
            original_content_str = original_content.decode(
                'utf-8') if isinstance(original_content, bytes) else original_content

        # Tạo CV record
        user_id = current_user.get("id")
        cv = CV(
            user_id=user_id,
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
        start_time = asyncio.get_event_loop().time()
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
            logger.error(
                f"CV {cv_id}: Lỗi từ CVProcessor: {analysis_result['error_message']}")
            raise ValueError(analysis_result["error_message"])

        # Cập nhật thông tin cơ bản
        basic_analysis = analysis_result.get("basic_analysis", {})
        cv.personal_info = basic_analysis.get("personal_info", {})
        cv.education = basic_analysis.get("education", [])
        cv.certifications = basic_analysis.get("certifications", [])
        cv.experiences = basic_analysis.get("experience", [])
        cv.skills = basic_analysis.get("skills", [])
        cv.analysis = basic_analysis.get("analysis", {})

        # Cập nhật phân tích career
        career_analysis = analysis_result.get("career_analysis", {})
        cv.strengths = career_analysis.get("strengths", [])
        cv.weaknesses = career_analysis.get("weaknesses", [])
        cv.skill_gaps = career_analysis.get("skill_gaps", [])
        cv.career_paths = career_analysis.get("career_paths", [])
        cv.recommended_skills = career_analysis.get("recommended_skills", [])
        cv.recommended_actions = career_analysis.get("recommended_actions", [])
        cv.analysis_summary = career_analysis.get("analysis_summary", {})

        # Cập nhật career matches và related data
        career_matches = analysis_result.get("career_matches", [])
        cv.career_matches = career_matches
        cv.preferred_industries = list(set([
            match.get("industry", "").strip()
            for match in career_matches
            if match.get("industry")
        ]))

        # Lưu vector embedding
        cv.embedding_vector = analysis_result.get("embedding_vector")
        
        # Cập nhật quality assessment
        quality_assessment = analysis_result.get("quality_assessment", {})
        cv.overall_score = quality_assessment.get("overall_score")
        cv.completeness = quality_assessment.get("completeness")
        cv.formatting = quality_assessment.get("formatting")
        cv.section_scores = quality_assessment.get("section_scores", {})
        cv.language_quality = quality_assessment.get("language_quality")
        cv.ats_compatibility = quality_assessment.get("ats_compatibility")
        cv.detailed_metrics = quality_assessment.get("detailed_metrics", {})
        cv.improvement_priority = quality_assessment.get("improvement_priority")
        
        # Cập nhật trạng thái và thời gian
        cv.analysis_status = "completed"
        cv.last_analyzed_at = datetime.utcnow()
        end_time = asyncio.get_event_loop().time()
        logger.info(f"CV {cv_id}: Phân tích hoàn tất trong {end_time - start_time:.2f} giây")
        try:
            db.commit()
            logger.info(f"CV {cv_id}: Đã lưu thành công vào database")
        except Exception as db_error:
            logger.error(
                f"Database error while saving CV analysis: {str(db_error)}")
            raise

    except Exception as e:
        error_msg = f"Lỗi khi phân tích CV {cv_id}: {str(e)}"
        logger.error(f"CV {cv_id}: {error_msg}")
        logger.error(f"CV {cv_id}: Stacktrace:", exc_info=True)

        if cv:
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
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")

    # Thêm task phân tích vào background
    background_tasks.add_task(run_analysis, cv_id, db)

    return {"status": "processing", "message": "Đang phân tích CV"}


@router.get("/{cv_id}/analyze", response_model=ResumeAnalysisResponse)
async def get_analysis(
    *,
    cv_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Lấy kết quả phân tích CV
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV không tồn tại")

    if cv.analysis_status == "failed":
        raise HTTPException(
            status_code=500, detail=cv.analysis_error or "Phân tích thất bại")

    if cv.analysis_status == "processing":
        return {"status": "processing", "message": "Đang phân tích CV"}

    if cv.analysis_status == "failed":
        return {
            "status": "failed",
            "error": cv.analysis_error or "Phân tích thất bại"
        }

    response = {
        "status": cv.analysis_status,
        "basic_analysis": {
            "personal_info": cv.personal_info,
            "education": cv.education,
            "certifications": cv.certifications,
            "experiences": cv.experiences,
            "skills": cv.skills,
            "analysis": cv.analysis
        },
        "career_analysis": {
            "strengths": cv.strengths,
            "weaknesses": cv.weaknesses,
            "skill_gaps": cv.skill_gaps,
            "career_paths": cv.career_paths,
            "recommended_skills": cv.recommended_skills,
            "recommended_actions": cv.recommended_actions,
            "analysis_summary": cv.analysis_summary,
            "career_matches": cv.career_matches,
            "preferred_industries": cv.preferred_industries,
        },
        "quality_assessment": {
            "overall": cv.overall_score,
            "completeness": cv.completeness,
            "formatting": cv.formatting,
            "section_scores": cv.section_scores,
            "language_quality": cv.language_quality,
            "ats_compatibility": cv.ats_compatibility,
            "improvement_priority": cv.improvement_priority,
        },
        "metrics": {
            "detailed": cv.detailed_metrics or {},
            "word_count": len(cv.extracted_text.split()) if cv.extracted_text else 0,
            "sections_count": len(cv.experiences or []) + len(cv.education or [])
        },
        "analysis_status": cv.analysis_status,
        "last_analyzed_at": cv.last_analyzed_at,
        "created_at": cv.created_at,
        "updated_at": cv.updated_at
    }
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
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        raise HTTPException(
            status_code=404,
            detail="CV không tồn tại hoặc không thuộc về người dùng này"
        )
    return cv
