import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from functools import wraps

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.redis_service import RedisService
from app.services.redis_service import RedisService

# Cấu hình logging
logger = logging.getLogger(__name__)

# Khởi tạo OpenAI client với OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

# Cấu hình headers cho OpenRouter
extra_headers = {
    "HTTP-Referer": settings.SITE_URL,
    "X-Title": settings.SITE_NAME,
}

# Hàm để tạo embeddings
def with_timeout(timeout_seconds: int = 30):
    """
    Decorator để thêm timeout cho các hàm async.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise Exception(f"Operation timed out after {timeout_seconds} seconds")
        return wrapper
    return decorator

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(5))
async def create_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho văn bản đầu vào sử dụng sentence-transformers.
    
    Args:
        text: Văn bản đầu vào.
        
    Returns:
        List[float]: Vector embedding.
    """
    try:
        # Kiểm tra cache
        redis_service = RedisService.get_instance()
        cache_key = redis_service.generate_cache_key("embedding", text[:50])
        cached_embedding = redis_service.get_cache(cache_key)
        
        if cached_embedding:
            return cached_embedding
            
        # Tạo embedding với sentence-transformers
        embedding_service = EmbeddingService.get_instance()
        embedding = embedding_service.create_embedding(text)
        
        # Lưu vào cache
        redis_service.set_cache(cache_key, embedding, expiry=86400)  # Cache 24h
        
        return embedding
    except Exception as e:
        logger.error(f"Lỗi khi tạo embedding: {str(e)}")
        raise

# Hàm để phân tích hồ sơ nghề nghiệp
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=60)
async def analyze_career_profile(
    skills: List[str],
    experiences: List[Dict[str, Any]],
    education: List[Dict[str, Any]],
    career_goals: List[str],
    preferred_industries: List[str]
) -> Dict[str, Any]:
    """
    Phân tích hồ sơ sự nghiệp và đưa ra khuyến nghị.
    
    Args:
        skills: Danh sách kỹ năng.
        experiences: Danh sách kinh nghiệm làm việc.
        education: Danh sách học vấn.
        career_goals: Mục tiêu nghề nghiệp.
        preferred_industries: Ngành công nghiệp ưa thích.
        
    Returns:
        Dict[str, Any]: Kết quả phân tích với các khuyến nghị.
    """
    try:
        # Chuẩn bị dữ liệu đầu vào
        profile_data = {
            "skills": skills,
            "experiences": experiences,
            "education": education,
            "career_goals": career_goals,
            "preferred_industries": preferred_industries
        }
        
        # Tạo prompt
        prompt = f"""
        Bạn là AI Career Advisor, một chuyên gia tư vấn nghề nghiệp. 
        Hãy phân tích hồ sơ nghề nghiệp dưới đây và đưa ra các gợi ý phát triển.
        
        Hồ sơ nghề nghiệp:
        {json.dumps(profile_data, ensure_ascii=False)}
        
        Yêu cầu:
        1. Phân tích điểm mạnh và điểm yếu dựa trên thông tin được cung cấp.
        2. Xác định khoảng cách kỹ năng dựa trên mục tiêu nghề nghiệp.
        3. Đề xuất tối đa 5 hướng phát triển nghề nghiệp phù hợp.
        4. Đề xuất top 5 kỹ năng cần phát triển và lý do.
        5. Đề xuất các hành động cụ thể để phát triển nghề nghiệp.
        
        Định dạng phản hồi của bạn dưới dạng JSON với cấu trúc sau:
        {{
            "strengths": ["Strength 1", "Strength 2", ...],
            "weaknesses": ["Weakness 1", "Weakness 2", ...],
            "skill_gaps": [
                {{"skill": "Skill 1", "importance": "High", "reason": "Reason 1"}},
                ...
            ],
            "career_paths": [
                {{"path": "Career 1", "fit_score": 8.5, "description": "Description 1"}},
                ...
            ],
            "recommended_skills": [
                {{"skill": "Skill 1", "reason": "Reason 1"}},
                ...
            ],
            "recommended_actions": [
                {{"action": "Action 1", "priority": "High", "description": "Description 1"}},
                ...
            ],
            "analysis_summary": "Tóm tắt tổng quan về phân tích và gợi ý."
        }}
        
        Đảm bảo phản hồi của bạn chỉ chứa JSON hợp lệ, không có văn bản giới thiệu hoặc giải thích.
        """
        
        # Kiểm tra cache
        redis_service = RedisService.get_instance()
        cache_key = redis_service.generate_cache_key(
            "career_analysis",
            "_".join(skills[:3]),  # Sử dụng 3 kỹ năng đầu tiên làm key
            "_".join(str(exp['title']) for exp in experiences[:2])  # 2 kinh nghiệm đầu
        )
        cached_result = redis_service.get_cache(cache_key)
        
        if cached_result:
            return cached_result

        # Gọi API nếu không có trong cache
        response = await client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là AI Career Advisor, một hệ thống tư vấn nghề nghiệp bằng AI. Bạn phân tích dữ liệu và đưa ra khuyến nghị."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # Xử lý phản hồi
        result_text = response.choices[0].message.content.strip()
        
        # Chuyển đổi phản hồi thành JSON
        try:
            # Xử lý kết quả để đảm bảo chỉ lấy phần JSON
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
                    
            result_data = json.loads(result_text.strip())
            return result_data
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi xử lý JSON: {str(e)}")
            logger.error(f"Dữ liệu nhận được: {result_text}")
            raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
            
    except Exception as e:
        logger.error(f"Lỗi khi phân tích hồ sơ: {str(e)}")
        raise

# Hàm để phân tích CV
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def analyze_cv_content(cv_text: str) -> Dict[str, Any]:
    """
    Phân tích nội dung CV và trích xuất thông tin quan trọng.
    
    Args:
        cv_text: Nội dung CV dạng text.
        
    Returns:
        Dict[str, Any]: Kết quả phân tích CV với các thông tin được cấu trúc.
    """
    try:
        # Tạo prompt
        prompt = f"""
        Phân tích CV sau và trích xuất thông tin chi tiết theo cấu trúc:

        CV Content:
        {cv_text}

        Yêu cầu:
        1. Trích xuất thông tin cá nhân
        2. Phân tích học vấn và chứng chỉ
        3. Phân tích kinh nghiệm làm việc
        4. Đánh giá kỹ năng
        5. Đề xuất hướng phát triển

        Định dạng phản hồi JSON:
        {{
            "personal_info": {{
                "name": "Tên người dùng",
                "email": "email@example.com",
                "phone": "Số điện thoại",
                "location": "Địa chỉ"
            }},
            "education": [
                {{
                    "degree": "Tên bằng cấp",
                    "institution": "Tên trường",
                    "year": "Năm tốt nghiệp",
                    "major": "Chuyên ngành",
                    "achievements": ["Thành tích 1", "Thành tích 2"]
                }}
            ],
            "certifications": [
                {{
                    "name": "Tên chứng chỉ",
                    "issuer": "Tổ chức cấp",
                    "year": "Năm cấp"
                }}
            ],
            "experience": [
                {{
                    "position": "Vị trí",
                    "company": "Tên công ty",
                    "duration": "Thời gian làm việc",
                    "responsibilities": ["Trách nhiệm 1", "Trách nhiệm 2"],
                    "achievements": ["Thành tích 1", "Thành tích 2"]
                }}
            ],
            "skills": {{
                "technical": ["Kỹ năng 1", "Kỹ năng 2"],
                "soft": ["Kỹ năng mềm 1", "Kỹ năng mềm 2"],
                "languages": ["Ngôn ngữ 1", "Ngôn ngữ 2"]
            }},
            "analysis": {{
                "strengths": ["Điểm mạnh 1", "Điểm mạnh 2"],
                "weaknesses": ["Điểm yếu 1", "Điểm yếu 2"],
                "career_recommendations": [
                    {{
                        "position": "Vị trí đề xuất",
                        "reason": "Lý do phù hợp",
                        "required_skills": ["Kỹ năng cần có 1", "Kỹ năng cần có 2"]
                    }}
                ],
                "development_suggestions": [
                    {{
                        "area": "Lĩnh vực cần phát triển",
                        "suggestion": "Đề xuất cụ thể",
                        "resources": ["Nguồn học 1", "Nguồn học 2"]
                    }}
                ]
            }}
        }}
        
        Đảm bảo phản hồi của bạn chỉ chứa JSON hợp lệ, không có văn bản giới thiệu hoặc giải thích.
        """
        
        # Gọi API
        response = client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là AI CV Analyzer, một hệ thống phân tích CV chuyên nghiệp. Bạn phân tích kỹ lưỡng và đưa ra nhận xét chi tiết về CV."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2500
        )
        
        # Xử lý phản hồi
        result_text = response.choices[0].message.content.strip()
        
        # Chuyển đổi phản hồi thành JSON
        try:
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
                    
            result_data = json.loads(result_text.strip())
            return result_data
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi xử lý JSON: {str(e)}")
            logger.error(f"Dữ liệu nhận được: {result_text}")
            raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
            
    except Exception as e:
        logger.error(f"Lỗi khi phân tích CV: {str(e)}")
        raise

# Hàm để xác định khoảng cách kỹ năng
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=45)
async def identify_skill_gaps(
    current_skills: List[str],
    target_career: str,
    experience_level: str = "entry"  # entry, mid, senior
) -> Dict[str, Any]:
    """
    Xác định khoảng cách kỹ năng giữa các kỹ năng hiện tại và các kỹ năng cần thiết cho nghề nghiệp mục tiêu.
    
    Args:
        current_skills: Danh sách kỹ năng hiện tại.
        target_career: Nghề nghiệp mục tiêu.
        experience_level: Cấp độ kinh nghiệm mong muốn.
        
    Returns:
        Dict[str, Any]: Kết quả phân tích khoảng cách kỹ năng.
    """
    try:
        # Tạo prompt
        prompt = f"""
        Xác định khoảng cách kỹ năng giữa kỹ năng hiện tại của người dùng và các kỹ năng cần thiết cho vị trí {target_career} ở cấp độ {experience_level}.
        
        Kỹ năng hiện tại:
        {json.dumps(current_skills, ensure_ascii=False)}
        
        Vị trí mục tiêu: {target_career}
        Cấp độ kinh nghiệm: {experience_level}
        
        Hãy xác định:
        1. Các kỹ năng thiếu cho vị trí này
        2. Mức độ quan trọng của từng kỹ năng (Cao, Trung bình, Thấp)
        3. Gợi ý các cách để phát triển những kỹ năng này
        4. Điểm khoảng cách kỹ năng tổng thể (thang điểm 0-10, 0 = không có khoảng cách, 10 = khoảng cách lớn)
        
        Định dạng phản hồi của bạn dưới dạng JSON với cấu trúc sau:
        {{
            "current_skills": ["Skill 1", "Skill 2", ...],
            "missing_skills": [
                {{"skill": "Skill 1", "importance": "High", "development_suggestion": "Suggestion 1"}},
                ...
            ],
            "skill_gap_score": 7.5,
            "recommendations": [
                {{"resource": "Resource 1", "type": "Course", "url": "https://example.com"}},
                ...
            ]
        }}
        
        Đảm bảo phản hồi của bạn chỉ chứa JSON hợp lệ, không có văn bản giới thiệu hoặc giải thích.
        """
        
        # Gọi API
        response = client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là AI Career Advisor, một hệ thống tư vấn nghề nghiệp bằng AI. Bạn phân tích dữ liệu và đưa ra khuyến nghị."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        # Xử lý phản hồi
        result_text = response.choices[0].message.content.strip()
        
        # Chuyển đổi phản hồi thành JSON
        try:
            # Xử lý kết quả để đảm bảo chỉ lấy phần JSON
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "", 1)
                if "```" in result_text:
                    result_text = result_text.split("```")[0]
                    
            result_data = json.loads(result_text.strip())
            return result_data
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi xử lý JSON: {str(e)}")
            logger.error(f"Dữ liệu nhận được: {result_text}")
            raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
            
    except Exception as e:
        logger.error(f"Lỗi khi xác định khoảng cách kỹ năng: {str(e)}")
        raise 