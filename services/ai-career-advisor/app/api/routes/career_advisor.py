import json
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import parse_obj_as
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.career_profile import CareerProfile
from app.models.career_pathway import CareerPathway
from app.models.user import User
from app.schemas.career_profile import (
    CareerAnalysisRequest,
    CareerRecommendationResponse,
    CareerPathway as CareerPathwaySchema,
    SkillGapResponse,
)
from app.services.openai_service import analyze_career_profile, identify_skill_gaps
from app.services.pinecone_service import search_career_pathways, store_career_pathway

router = APIRouter()


@router.post("/analyze", response_model=CareerRecommendationResponse)
def analyze_profile(
    *,
    db: Session = Depends(get_db),
    analysis_request: CareerAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Phân tích hồ sơ nghề nghiệp và đưa ra khuyến nghị.
    """
    # Kiểm tra nếu có profile_id được cung cấp
    if analysis_request.profile_id:
        career_profile = (
            db.query(CareerProfile)
            .filter(
                CareerProfile.id == analysis_request.profile_id,
                CareerProfile.user_id == current_user.id,
            )
            .first()
        )
        if not career_profile:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ nghề nghiệp")
    
    # Sử dụng thông tin từ profile hoặc từ request
    skills = json.loads(current_user.skills) if current_user.skills else []
    experiences = json.loads(current_user.experiences) if current_user.experiences else []
    education = json.loads(current_user.education) if current_user.education else []
    career_goals = json.loads(current_user.career_goals) if current_user.career_goals else []
    preferred_industries = json.loads(current_user.preferred_industries) if current_user.preferred_industries else []
    
    # Ghi đè với thông tin từ request nếu có
    if analysis_request.skills:
        skills = analysis_request.skills
    if analysis_request.experiences:
        experiences = analysis_request.experiences
    if analysis_request.education:
        education = analysis_request.education
    if analysis_request.career_goals:
        career_goals = analysis_request.career_goals
    if analysis_request.preferred_industries:
        preferred_industries = analysis_request.preferred_industries
    
    # Gọi service phân tích hồ sơ
    analysis_result = analyze_career_profile(
        skills=skills,
        experiences=experiences,
        education=education,
        career_goals=career_goals,
        preferred_industries=preferred_industries
    )
    
    # Lưu kết quả phân tích vào career profile nếu có
    if analysis_request.profile_id:
        career_profile.strengths = json.dumps(analysis_result.get("strengths", []))
        career_profile.weaknesses = json.dumps(analysis_result.get("weaknesses", []))
        career_profile.skill_gaps = json.dumps(analysis_result.get("skill_gaps", []))
        career_profile.recommended_career_paths = json.dumps(analysis_result.get("career_paths", []))
        career_profile.recommended_skills = json.dumps(analysis_result.get("recommended_skills", []))
        career_profile.recommended_actions = json.dumps(analysis_result.get("recommended_actions", []))
        
        db.add(career_profile)
        db.commit()
        db.refresh(career_profile)
    
    # Tạo response
    return {
        "career_paths": analysis_result.get("career_paths", []),
        "skills_to_develop": analysis_result.get("recommended_skills", []),
        "actions": analysis_result.get("recommended_actions", []),
        "analysis_summary": analysis_result.get("analysis_summary", "")
    }


@router.get("/recommendations", response_model=List[CareerPathwaySchema])
def get_career_recommendations(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    query: str = Query(None, description="Truy vấn tìm kiếm"),
    top_k: int = Query(5, description="Số lượng kết quả tối đa"),
) -> Any:
    """
    Tìm kiếm các hướng nghề nghiệp phù hợp.
    """
    # Lấy thông tin kỹ năng và ngành công nghiệp ưa thích của người dùng
    skills = json.loads(current_user.skills) if current_user.skills else []
    preferred_industries = json.loads(current_user.preferred_industries) if current_user.preferred_industries else []
    
    # Mặc định sử dụng "career suggestions" nếu không có query
    search_query = query if query else "career suggestions"
    
    # Tìm kiếm career pathways
    pathways = search_career_pathways(
        query=search_query,
        skills=skills,
        industries=preferred_industries if preferred_industries else None,
        top_k=top_k
    )
    
    # Chuyển đổi kết quả thành danh sách career pathways
    career_pathways = []
    for p in pathways:
        pathway = CareerPathway(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            industry=p["industry"],
            required_skills=json.dumps(p["required_skills"]),
            required_experience=p["required_experience"]
        )
        
        # Thêm thông tin tùy chọn
        if "salary_range_min" in p:
            pathway.salary_range_min = p["salary_range_min"]
        if "salary_range_max" in p:
            pathway.salary_range_max = p["salary_range_max"]
        if "growth_potential" in p:
            pathway.growth_potential = p["growth_potential"]
            
        career_pathways.append(pathway)
        
    # Nếu không có kết quả và chưa có career pathways trong DB
    if not career_pathways and db.query(CareerPathway).count() == 0:
        # Tạo một số career pathways demo
        demo_pathways = [
            {
                "name": "Data Scientist",
                "description": "Phân tích và diễn giải dữ liệu phức tạp để đưa ra quyết định dựa trên dữ liệu.",
                "industry": "Information Technology",
                "required_skills": ["Python", "Machine Learning", "SQL", "Statistics", "Data Visualization"],
                "required_experience": 2,
                "salary_range_min": 80000.0,
                "salary_range_max": 150000.0,
                "growth_potential": 9.0
            },
            {
                "name": "Full Stack Developer",
                "description": "Phát triển cả phần front-end và back-end của ứng dụng web.",
                "industry": "Information Technology",
                "required_skills": ["JavaScript", "React", "Node.js", "SQL", "Git"],
                "required_experience": 3,
                "salary_range_min": 70000.0,
                "salary_range_max": 140000.0,
                "growth_potential": 8.5
            },
            {
                "name": "Product Manager",
                "description": "Định hướng chiến lược sản phẩm và phát triển các tính năng mới.",
                "industry": "Product Management",
                "required_skills": ["Product Strategy", "User Research", "Agile Methodologies", "Communication", "Data Analysis"],
                "required_experience": 4,
                "salary_range_min": 90000.0,
                "salary_range_max": 160000.0,
                "growth_potential": 8.7
            }
        ]
        
        # Lưu demo pathways vào DB và Pinecone
        for idx, p in enumerate(demo_pathways):
            pathway = CareerPathway(
                name=p["name"],
                description=p["description"],
                industry=p["industry"],
                required_skills=json.dumps(p["required_skills"]),
                required_experience=p["required_experience"],
                salary_range_min=p["salary_range_min"],
                salary_range_max=p["salary_range_max"],
                growth_potential=p["growth_potential"]
            )
            db.add(pathway)
            db.flush()  # Để lấy ID
            
            # Lưu vào Pinecone
            store_career_pathway(
                pathway_id=pathway.id,
                name=pathway.name,
                description=pathway.description,
                industry=pathway.industry,
                required_skills=p["required_skills"],
                required_experience=pathway.required_experience,
                salary_range_min=pathway.salary_range_min,
                salary_range_max=pathway.salary_range_max,
                growth_potential=pathway.growth_potential
            )
            
            career_pathways.append(pathway)
        
        db.commit()
    
    return career_pathways


@router.get("/skill-gaps", response_model=SkillGapResponse)
def get_skill_gaps(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    target_career: str = Query(..., description="Nghề nghiệp mục tiêu"),
    experience_level: str = Query("entry", description="Cấp độ kinh nghiệm (entry, mid, senior)")
) -> Any:
    """
    Phân tích khoảng cách kỹ năng cho một nghề nghiệp mục tiêu.
    """
    # Lấy danh sách kỹ năng hiện tại của người dùng
    current_skills = json.loads(current_user.skills) if current_user.skills else []
    
    # Gọi service phân tích khoảng cách kỹ năng
    skill_gap_analysis = identify_skill_gaps(
        current_skills=current_skills,
        target_career=target_career,
        experience_level=experience_level
    )
    
    return skill_gap_analysis 