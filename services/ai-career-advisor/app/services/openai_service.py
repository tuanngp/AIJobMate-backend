import json
import logging
from typing import Any, Dict, List, Optional

import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings

# Cấu hình logging
logger = logging.getLogger(__name__)

# Cấu hình API key
openai.api_key = settings.OPENAI_API_KEY

# Hàm để tạo embeddings
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(5))
def create_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho văn bản đầu vào sử dụng OpenAI API.
    
    Args:
        text: Văn bản đầu vào.
        
    Returns:
        List[float]: Vector embedding.
    """
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        logger.error(f"Lỗi khi tạo embedding: {str(e)}")
        raise

# Hàm để phân tích hồ sơ nghề nghiệp
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def analyze_career_profile(
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
        
        # Gọi API
        response = openai.chat.completions.create(
            model=settings.GPT_MODEL,
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

# Hàm để xác định khoảng cách kỹ năng
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def identify_skill_gaps(
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
        response = openai.chat.completions.create(
            model=settings.GPT_MODEL,
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