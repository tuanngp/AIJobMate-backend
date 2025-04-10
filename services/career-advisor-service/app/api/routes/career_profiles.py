import json
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.career_profile import CareerProfile
from app.models.user import User
from app.schemas.career_profile import (
    CareerProfile as CareerProfileSchema,
    CareerProfileCreate,
    CareerProfileUpdate,
)
from app.services.openai_service import create_embedding

router = APIRouter()


@router.post("/", response_model=CareerProfileSchema)
def create_career_profile(
    *,
    db: Session = Depends(get_db),
    career_profile_in: CareerProfileCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Tạo hồ sơ nghề nghiệp mới.
    """
    # Tạo text để embedding
    text_to_embed = f"{career_profile_in.title}. {career_profile_in.description}."
    # Tạo embedding vector và chuyển thành JSON để lưu trữ
    embedding = create_embedding(text_to_embed)
    embedding_json = json.dumps(embedding)
    
    # Tạo đối tượng career profile
    career_profile = CareerProfile(
        title=career_profile_in.title,
        description=career_profile_in.description,
        user_id=current_user.id,
        embedding_vector=embedding_json
    )
    
    db.add(career_profile)
    db.commit()
    db.refresh(career_profile)
    return career_profile


@router.get("/", response_model=List[CareerProfileSchema])
def read_career_profiles(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Lấy danh sách hồ sơ nghề nghiệp của người dùng hiện tại.
    """
    career_profiles = (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return career_profiles


@router.get("/{profile_id}", response_model=CareerProfileSchema)
def read_career_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: str = Path(..., title="ID của hồ sơ nghề nghiệp"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Lấy thông tin chi tiết của một hồ sơ nghề nghiệp.
    """
    career_profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.id == profile_id, CareerProfile.user_id == current_user.id)
        .first()
    )
    if not career_profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ nghề nghiệp")
    return career_profile


@router.put("/{profile_id}", response_model=CareerProfileSchema)
def update_career_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: str = Path(..., title="ID của hồ sơ nghề nghiệp"),
    career_profile_in: CareerProfileUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cập nhật thông tin hồ sơ nghề nghiệp.
    """
    career_profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.id == profile_id, CareerProfile.user_id == current_user.id)
        .first()
    )
    if not career_profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ nghề nghiệp")
    
    # Cập nhật các thông tin cơ bản
    update_data = career_profile_in.dict(exclude_unset=True)
    
    # Chuyển đổi các trường phức tạp thành JSON
    for field in ["strengths", "weaknesses", "skill_gaps", "recommended_career_paths", 
                 "recommended_skills", "recommended_actions"]:
        if field in update_data and update_data[field] is not None:
            update_data[field] = json.dumps(update_data[field])
    
    # Cập nhật embedding nếu title hoặc description thay đổi
    if "title" in update_data or "description" in update_data:
        title = update_data.get("title", career_profile.title)
        description = update_data.get("description", career_profile.description)
        text_to_embed = f"{title}. {description}."
        embedding = create_embedding(text_to_embed)
        update_data["embedding_vector"] = json.dumps(embedding)
    
    # Áp dụng các thay đổi
    for field, value in update_data.items():
        setattr(career_profile, field, value)
    
    db.add(career_profile)
    db.commit()
    db.refresh(career_profile)
    return career_profile


@router.delete("/{profile_id}", response_model=CareerProfileSchema)
def delete_career_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: str = Path(..., title="ID của hồ sơ nghề nghiệp"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Xóa hồ sơ nghề nghiệp.
    """
    career_profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.id == profile_id, CareerProfile.user_id == current_user.id)
        .first()
    )
    if not career_profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ nghề nghiệp")
    
    db.delete(career_profile)
    db.commit()
    return career_profile 