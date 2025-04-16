import json
import logging
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec
from tenacity import retry, stop_after_attempt, wait_random_exponential
from app.core.config import settings
from app.services.redis_service import RedisService
from app.services.openai_service import create_embedding


# Cấu hình logging
logger = logging.getLogger(__name__)

class PineconeClient:
    _instance = None
    _index = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if PineconeClient._instance is not None:
            raise Exception("PineconeClient là singleton class, sử dụng get_instance()")
        self.init_pinecone()

    def init_pinecone(self):
        """
        Khởi tạo kết nối đến Pinecone Vector Database.
        """
        try:
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Kiểm tra danh sách index hiện có
            existing_indexes = pc.list_indexes().names()
            
            # Kiểm tra và tạo index nếu chưa tồn tại
            if settings.PINECONE_INDEX not in existing_indexes:
                pc.create_index(
                    name=settings.PINECONE_INDEX,
                    dimension=768,  # Kích thước vector cho sentence-transformers phobert-base
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=settings.PINECONE_ENVIRONMENT
                    )
                )
            
            # Lưu index vào biến static
            PineconeClient._index = pc.Index(settings.PINECONE_INDEX)
            
        except Exception as e:
            logger.error(f"Lỗi chi tiết khi khởi tạo Pinecone: {str(e)}", exc_info=True)
            raise

    def get_index(self):
        """
        Lấy Pinecone index đã được khởi tạo.
        """
        if self._index is None:
            self.init_pinecone()
        return self._index

# Lưu career pathway vào Pinecone
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def store_career_pathway(
    pathway_id: str,
    name: str,
    description: str,
    required_skills: List[str],
    reason: str = "",
    industry: str = "",
    required_experience: int = 0,
    score: float = 0.8
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
        # Tạo embedding vector
        text_to_embed = f"{name}. {description}. Required skills: {', '.join(required_skills)}. {reason}"
        try:
            embedding = await create_embedding(text_to_embed)
            if isinstance(embedding, list):
                logger.info(f"Tạo embedding vector thành công cho {name}")
            else:
                logger.error(f"Embedding vector không đúng định dạng cho {name}")
                raise ValueError("Embedding vector phải là list")
        except Exception as e:
            logger.error(f"Lỗi khi tạo embedding cho {name}: {str(e)}")
            raise
        
        # Chuẩn bị metadata
        metadata = {
            "name": name,
            "description": description,
            "required_skills": json.dumps(required_skills),
            "reason": reason,
            "industry": industry,
            "required_experience": required_experience,
            "score": score
        }
        
        # Lấy Pinecone index từ singleton
        index = PineconeClient.get_instance().get_index()
        
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
async def search_career_pathways(
    query: str = "",
    embedding_vector: Optional[List[float]] = None,
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
        # Sử dụng embedding_vector nếu được cung cấp, nếu không tạo mới từ query
        query_embedding = embedding_vector
        if query_embedding is None and query:
            query_embedding = await create_embedding(query)
        
        if query_embedding is None:
            raise ValueError("Cần cung cấp embedding_vector hoặc query không rỗng")

        # Tạo bộ lọc nếu cần
        filter_dict = {}
        if industries:
            filter_dict["industry"] = {"$in": industries}
            
        # Kiểm tra cache
        redis_service = RedisService.get_instance()
        cache_key = redis_service.generate_cache_key(
            "career_search",
            query[:50],
            "_".join(industries) if industries else "all"
        )
        cached_results = await redis_service.get_cache(cache_key)
        
        if cached_results:
            return cached_results

        # Kết nối đến Pinecone nếu không có trong cache
        index = PineconeClient.get_instance().get_index()
        
        # Thực hiện tìm kiếm
        try:
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace="career_pathways",
                filter=filter_dict if filter_dict else None,
                include_metadata=True
            )
        except Exception as query_error:
            logger.error(f"Lỗi khi query Pinecone: {str(query_error)}", exc_info=True)
            raise
        # Xử lý kết quả
        pathways = []
        
        for i, match in enumerate(results.matches):
            # Parse required_skills từ JSON string
            required_skills = json.loads(match.metadata.get("required_skills", "[]"))
            logger.debug(f"Career pathway {i+1}: {match.metadata.get('name')} - Score: {match.score}")
            
            # Tính điểm phù hợp kỹ năng nếu có
            skill_match_score = 0
            if skills:
                matching_skills = set(skills) & set(required_skills)
                skill_match_score = len(matching_skills) / len(required_skills) if required_skills else 0
                logger.debug(f"Skill match score cho {match.metadata.get('name')}: {skill_match_score}")
            
            
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
        
        # Cache kết quả trong 1 giờ
        await redis_service.set_cache(cache_key, pathways, expiry=3600)
        return pathways
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm career pathways: {str(e)}", exc_info=True)
        raise