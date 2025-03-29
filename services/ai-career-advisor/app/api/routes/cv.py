from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.user import User
from app.models.cv import CV
from app.schemas.cv import CVCreate, CVInDB
from app.services.cv_processor import CVProcessor

router = APIRouter()

@router.post("/upload", response_model=CVInDB)
async def upload_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    file: UploadFile = File(...)
) -> CVInDB:
    """
    Upload CV file và trích xuất nội dung
    """
    try:
        # Xử lý file CV
        file_name, file_type, extracted_text = await CVProcessor.process_cv(file)
        
        # Lưu file content dưới dạng bytes
        file.seek(0)
        original_content = await file.read()
        
        # Tạo bản ghi CV trong database
        cv = CV(
            user_id=current_user.id,
            file_name=file_name,
            file_type=file_type,
            original_content=original_content.decode('utf-8'),
            extracted_text=extracted_text
        )
        
        db.add(cv)
        db.commit()
        db.refresh(cv)
        
        return cv
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Đã xảy ra lỗi khi xử lý CV: {str(e)}"
        )

@router.get("/list", response_model=List[CVInDB])
def list_cvs(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> List[CVInDB]:
    """
    Lấy danh sách CV của người dùng hiện tại
    """
    return db.query(CV).filter(CV.user_id == current_user.id).offset(skip).limit(limit).all()

@router.get("/{cv_id}", response_model=CVInDB)
def get_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    cv_id: int
) -> CVInDB:
    """
    Lấy thông tin chi tiết của một CV
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(
            status_code=404,
            detail="CV không tồn tại hoặc không thuộc về người dùng này"
        )
    return cv

@router.post("/{cv_id}/analyze")
def analyze_cv(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    cv_id: int
):
    """
    Phân tích nội dung CV bằng AI
    """
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == current_user.id).first()
    if not cv:
        raise HTTPException(
            status_code=404,
            detail="CV không tồn tại hoặc không thuộc về người dùng này"
        )
    
    analysis_result = CVProcessor.analyze_cv(cv.extracted_text)
    return analysis_result