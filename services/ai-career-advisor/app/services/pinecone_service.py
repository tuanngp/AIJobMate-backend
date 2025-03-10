import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import pinecone
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings
from app.services.openai_service import create_embedding

# Cấu hình logging
logger = logging.getLogger(__name__)

# Khởi tạo Pinecone client
def init_pinecone():
    """
    Khởi tạo kết nối đến Pinecone Vector Database.
    """
    try:
        pinecone.init(
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENVIRONMENT
        )
        
        # Kiểm tra và tạo index nếu chưa tồn tại
        if settings.PINECONE_INDEX not in pinecone.list_indexes():
            pinecone.create_index(
                name=settings.PINECONE_INDEX,
                dimension=1536,  # Kích thước vector cho text-embedding-ada-002
                metric="cosine"
            )
            logger.info(f"Đã tạo index {settings.PINECONE_INDEX} trong Pinecone")
        
        # Lấy index
        index = pinecone.Index(settings.PINECONE_INDEX)
        return index
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Pinecone: {str(e)}")
        raise

# Lưu career pathway vào Pinecone
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def store_career_pathway(
    pathway_id: str,
    name: str,
    description: str,
    industry: str,
    required_skills: List[str],
    required_experience: int,
    salary_range_min: Optional[float] = None,
    salary_range_max: Optional[float] = None,
    growth_potential: Optional[float] = None
) -> bool:
    """
    Lưu thông tin career pathway vào Pinecone.
    
    Args:
        pathway_id: ID của career pathway.
        name: Tên của career pathway.
        description: Mô tả của career pathway.
        industry: Ngành công nghiệp.
        required_skills: Các kỹ năng yêu cầu.
        required_experience: Kinh nghiệm yêu cầu (năm).
        salary_range_min: Lương tối thiểu.
        salary_range_max: Lương tối đa.
        growth_potential: Tiềm năng phát triển (1-10).
        
    Returns:
        bool: Trạng thái thành công.
    """
    try:
        # Tạo text để embedding
        text_to_embed = f"{name}. {description}. Industry: {industry}. Required skills: {', '.join(required_skills)}."
        
        # Tạo embedding vector
        embedding = create_embedding(text_to_embed)
        
        # Chuẩn bị metadata
        metadata = {
            "name": name,
            "description": description,
            "industry": industry,
            "required_skills": json.dumps(required_skills),
            "required_experience": required_experience
        }
        
        # Thêm thông tin tùy chọn
        if salary_range_min is not None:
            metadata["salary_range_min"] = salary_range_min
        if salary_range_max is not None:
            metadata["salary_range_max"] = salary_range_max
        if growth_potential is not None:
            metadata["growth_potential"] = growth_potential
        
        # Lấy Pinecone index
        index = init_pinecone()
        
        # Upsert vector vào Pinecone
        index.upsert(
            vectors=[
                {
                    "id": pathway_id,
                    "values": embedding,
                    "metadata": metadata
                }
            ],
            namespace="career_pathways"
        )
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu career pathway vào Pinecone: {str(e)}")
        raise

# Tìm kiếm career pathway phù hợp
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def search_career_pathways(
    query: str,
    skills: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm các career pathway phù hợp với truy vấn.
    
    Args:
        query: Truy vấn tìm kiếm.
        skills: Danh sách kỹ năng để lọc.
        industries: Danh sách ngành công nghiệp để lọc.
        top_k: Số lượng kết quả tối đa.
        
    Returns:
        List[Dict[str, Any]]: Danh sách các career pathway phù hợp.
    """
    try:
        # Tạo embedding vector cho truy vấn
        query_embedding = create_embedding(query)
        
        # Tạo bộ lọc nếu cần
        filter_dict = {}
        if industries:
            filter_dict["industry"] = {"$in": industries}
            
        # Kết nối đến Pinecone
        index = init_pinecone()
        
        # Thực hiện tìm kiếm
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace="career_pathways",
            filter=filter_dict if filter_dict else None,
            include_metadata=True
        )
        
        # Xử lý kết quả
        pathways = []
        for match in results.matches:
            # Parse required_skills từ JSON string
            required_skills = json.loads(match.metadata.get("required_skills", "[]"))
            
            # Tính điểm phù hợp kỹ năng nếu có
            skill_match_score = 0
            if skills:
                matching_skills = set(skills) & set(required_skills)
                skill_match_score = len(matching_skills) / len(required_skills) if required_skills else 0
            
            # Tạo đối tượng pathway
            pathway = {
                "id": match.id,
                "name": match.metadata.get("name"),
                "description": match.metadata.get("description"),
                "industry": match.metadata.get("industry"),
                "required_skills": required_skills,
                "required_experience": match.metadata.get("required_experience"),
                "similarity_score": match.score,
                "skill_match_score": skill_match_score
            }
            
            # Thêm thông tin tùy chọn
            if "salary_range_min" in match.metadata:
                pathway["salary_range_min"] = match.metadata.get("salary_range_min")
            if "salary_range_max" in match.metadata:
                pathway["salary_range_max"] = match.metadata.get("salary_range_max")
            if "growth_potential" in match.metadata:
                pathway["growth_potential"] = match.metadata.get("growth_potential")
            
            pathways.append(pathway)
        
        return pathways
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm career pathways: {str(e)}")
        raise 