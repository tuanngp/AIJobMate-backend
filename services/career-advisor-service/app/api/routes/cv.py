import asyncio
import logging
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List
from datetime import datetime

from app.api import deps
from app.models.cv import CV
from app.schemas.base import BaseResponseModel
from app.schemas.cv import CVInDB, ResumeAnalysisResponse
from app.services.cv_processor import CVProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=BaseResponseModel[CVInDB])
async def upload_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    file: UploadFile = File(...)
) -> CVInDB:
    """
    Upload and process CV file
    """
    try:
        # Xử lý file CV
        file_name, file_type, extracted_text = await CVProcessor.process_cv(file)
        if not file_name or not file_type or not extracted_text:
            return BaseResponseModel[CVInDB](
                code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Cannot process CV file",
                errors="File name, type or extracted text is missing"
            )

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

        return BaseResponseModel[CVInDB](
            code=status.HTTP_200_OK,
            message="CV uploaded successfully",
            data=cv
        )
    except Exception as e:
        error_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_message = "Error processing CV"

        if isinstance(e, FileNotFoundError):
            error_code = status.HTTP_404_NOT_FOUND
            error_message = "File not found"
        elif isinstance(e, PermissionError):
            error_code = status.HTTP_403_FORBIDDEN
            error_message = "Permission denied"
        elif isinstance(e, (TypeError, ValueError)):
            error_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            error_message = "Invalid file type or content"

        logger.error(f"Upload CV error: {str(e)}", exc_info=True)
        return BaseResponseModel(
            code=error_code,
            message=error_message,
            errors=str(e)
        )


async def run_analysis(cv_id: int, db: Session):
    """
    Process CV analysis in the background
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

        _update_cv_with_analysis(cv, analysis_result)

        # Cập nhật trạng thái và thời gian
        cv.analysis_status = "completed"
        cv.last_analyzed_at = datetime.utcnow()

        end_time = asyncio.get_event_loop().time()
        logger.info(
            f"CV {cv_id}: Phân tích hoàn tất trong {end_time - start_time:.2f} giây")

        db.commit()
        logger.info(f"CV {cv_id}: Đã lưu thành công vào database")

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

def run_analysis_sync(cv_id: int):
    """Phiên bản đồng bộ của run_analysis để chạy trong process riêng biệt"""
    from app.db.session import SessionLocal
    from app.api.routes.cv import run_analysis
    
    # Tạo session mới trong process riêng
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_analysis(cv_id, db))
    except Exception as e:
        logging.error(f"Error in run_analysis_sync for CV {cv_id}: {str(e)}", exc_info=True)
        
        try:
            cv = db.query(CV).filter(CV.id == cv_id).first()
            if cv:
                cv.analysis_status = "failed"
                cv.analysis_error = str(e)
                db.commit()
        except Exception as db_error:
            logging.error(f"Failed to update error status for CV {cv_id}: {str(db_error)}")
    finally:
        db.close()

def _update_cv_with_analysis(cv: CV, analysis_result: Dict[str, Any]) -> None:
    """
    Cập nhật CV với kết quả phân tích
    """
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


@router.post("/{cv_id}/analyze", response_model=BaseResponseModel[str])
async def analyze_cv(
    *,
    cv_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Analyze CV and store results in the database
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="CV not found or does not belong to this user",
            errors="CV not found or does not belong to this user"
        )

    if cv.analysis_status == "processing":
        return BaseResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="CV is already being analyzed",
            data="CV is already being analyzed"
        )

    if cv.analysis_status == "completed":
        return BaseResponseModel(
            code=status.HTTP_200_OK,
            message="CV analysis is already completed",
            data="CV analysis is already completed"
        )

    cv.analysis_status = "processing"
    cv.last_analyzed_at = datetime.utcnow()
    db.commit()
    
    from concurrent.futures import ProcessPoolExecutor
    executor = ProcessPoolExecutor(max_workers=2)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_analysis_sync, cv_id)

    return BaseResponseModel(
        code=status.HTTP_200_OK,
        message="CV analysis started successfully",
        data="CV analysis started successfully"
    )


@router.get("/{cv_id}/analyze", response_model=BaseResponseModel[ResumeAnalysisResponse])
async def get_analysis(
    *,
    cv_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get CV analysis results
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="CV not found or does not belong to this user",
            errors="CV not found or does not belong to this user"
        )

    if cv.analysis_status == "failed":
        return BaseResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="CV analysis failed",
            data=cv.analysis_error
        )

    if cv.analysis_status == "processing":
        return BaseResponseModel(
            code=status.HTTP_202_ACCEPTED,
            message="CV is being analyzed",
            data="CV is being analyzed"
        )
        
    if cv.analysis_status == "pending":
        return BaseResponseModel(
            code=status.HTTP_202_ACCEPTED,
            message="CV analysis is pending",
            data="CV analysis is pending"
        )
        
    if not cv.analysis_status == "completed":
        return BaseResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="CV analysis is not completed",
            data="CV analysis is not completed"
        )
        
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
    return BaseResponseModel[ResumeAnalysisResponse](
        code=status.HTTP_200_OK,
        message="Get CV analysis successfully",
        data=response
    )


@router.get("/list", response_model=BaseResponseModel[List[CVInDB]])
def list_cvs(
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> BaseResponseModel[List[CVInDB]]:
    """
    Get list of CVs for the current user
    """
    list_cvs = (db.query(CV)
                .filter(CV.user_id == current_user.get("id"))
                .order_by(CV.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all())
    if not list_cvs:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="No CVs found",
            data=[]
        )
    return BaseResponseModel[List[CVInDB]](
        code=status.HTTP_200_OK,
        message="Get list of CVs successfully",
        data=list_cvs
    )


@router.get("/{cv_id}", response_model=BaseResponseModel[CVInDB])
def get_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    cv_id: int
) -> BaseResponseModel[CVInDB]:
    """
    Get CV by ID for the current user
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id ==
                             current_user.get("id")).first()
    if not cv:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="CV not found or does not belong to this user",
            errors="CV not found or does not belong to this user"
        )
    return BaseResponseModel[CVInDB](
        code=status.HTTP_200_OK,
        message="Get CV successfully",
        data=cv
    )
