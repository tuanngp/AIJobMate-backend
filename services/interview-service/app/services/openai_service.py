import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from functools import wraps

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings

# Cấu hình logging
logger = logging.getLogger(__name__)

# Khởi tạo OpenAI client với OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

# Cấu hình headers cho OpenRouter
extra_headers = {
    "HTTP-Referer": settings.SITE_URL,  # Trang web của bạn
    "X-Title": settings.SITE_NAME,      # Tên ứng dụng của bạn
    "Content-Type": "application/json"
}

def with_timeout(timeout_seconds: int = 60):
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

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=60)
async def generate_interview_questions(
    job_title: str,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    num_questions: int = 5,
    difficulty_level: str = "medium",
    interview_type: str = "mixed",
    skills_required: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Sử dụng AI để tạo câu hỏi phỏng vấn dựa trên các tiêu chí đầu vào.
    
    Args:
        job_title: Tên vị trí công việc.
        job_description: Mô tả công việc (tùy chọn).
        industry: Ngành công nghiệp (tùy chọn).
        num_questions: Số lượng câu hỏi cần tạo.
        difficulty_level: Mức độ khó (easy, medium, hard).
        interview_type: Loại phỏng vấn (technical, behavioral, mixed).
        skills_required: Danh sách kỹ năng yêu cầu (tùy chọn).
        
    Returns:
        List[Dict[str, Any]]: Danh sách các câu hỏi phỏng vấn với thông tin liên quan.
    """
    try:
        # Chuẩn bị dữ liệu đầu vào
        input_data = {
            "job_title": job_title,
            "job_description": job_description or "",
            "industry": industry or "",
            "num_questions": num_questions,
            "difficulty_level": difficulty_level,
            "interview_type": interview_type,
            "skills_required": skills_required or []
        }
        
        # Tạo prompt
        prompt = f"""
        Bạn là AI Interview Assistant, một trợ lý tạo câu hỏi phỏng vấn chuyên nghiệp.
        Hãy tạo {num_questions} câu hỏi phỏng vấn cho vị trí {job_title} với các thông tin sau:
        
        - Mô tả công việc: {job_description or 'Không có thông tin'}
        - Ngành: {industry or 'Không có thông tin'} 
        - Mức độ khó: {difficulty_level}
        - Loại phỏng vấn: {interview_type}
        - Kỹ năng yêu cầu: {', '.join(skills_required) if skills_required else 'Không có thông tin cụ thể'}
        
        Quy tắc:
        1. Nếu loại phỏng vấn là "technical", tập trung vào các câu hỏi kỹ thuật liên quan đến vị trí.
        2. Nếu loại phỏng vấn là "behavioral", tập trung vào câu hỏi về hành vi, tình huống và kỹ năng mềm.
        3. Nếu loại phỏng vấn là "mixed", kết hợp cả hai loại câu hỏi trên.
        4. Độ khó của câu hỏi phải phù hợp với mức độ khó đã chọn.
        5. Mỗi câu hỏi phải có một câu trả lời mẫu chất lượng cao.
        
        Hãy trả về kết quả dưới dạng JSON với cấu trúc sau:
        [
            {{
                "question": "Nội dung câu hỏi",
                "question_type": "technical/behavioral/situational",
                "difficulty": "easy/medium/hard",
                "category": "Danh mục của câu hỏi (ví dụ: programming, database, teamwork, leadership...)",
                "sample_answer": "Câu trả lời mẫu chi tiết"
            }},
            ...
        ]
        
        Đảm bảo phản hồi của bạn chỉ chứa JSON hợp lệ, không có văn bản giới thiệu hoặc giải thích.
        """
        
        # Gọi API
        response = await client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là AI Interview Assistant, một hệ thống tạo ra các câu hỏi phỏng vấn thông minh và đánh giá câu trả lời."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
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
                    
            questions = json.loads(result_text.strip())
            return questions
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi xử lý JSON: {str(e)}")
            logger.error(f"Dữ liệu nhận được: {result_text}")
            raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
            
    except Exception as e:
        logger.error(f"Lỗi khi tạo câu hỏi phỏng vấn: {str(e)}")
        raise

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=45)
async def analyze_interview_answer(
    question: str,
    question_type: str,
    user_answer: str,
    job_title: str
) -> Dict[str, Any]:
    """
    Phân tích câu trả lời phỏng vấn của người dùng và đưa ra phản hồi.
    
    Args:
        question: Câu hỏi phỏng vấn.
        question_type: Loại câu hỏi (technical, behavioral, situational).
        user_answer: Câu trả lời của người dùng.
        job_title: Vị trí công việc.
        
    Returns:
        Dict[str, Any]: Phản hồi AI về câu trả lời của người dùng.
    """
    try:
        # Tạo prompt
        prompt = f"""
        Bạn là AI Interview Evaluator, một chuyên gia đánh giá câu trả lời phỏng vấn.
        Hãy đánh giá câu trả lời dưới đây cho vị trí {job_title}.
        
        Câu hỏi ({question_type}): {question}
        
        Câu trả lời của ứng viên: {user_answer}
        
        Yêu cầu:
        1. Đánh giá điểm mạnh và điểm yếu của câu trả lời.
        2. Đề xuất cách cải thiện câu trả lời.
        3. Đánh giá mức độ phù hợp của câu trả lời với câu hỏi.
        4. Cho điểm từ 1-10 dựa trên chất lượng câu trả lời.
        
        Hãy trả về kết quả dưới dạng JSON với cấu trúc sau:
        {{
            "strengths": ["Điểm mạnh 1", "Điểm mạnh 2", ...],
            "weaknesses": ["Điểm yếu 1", "Điểm yếu 2", ...],
            "improvement_suggestions": ["Gợi ý 1", "Gợi ý 2", ...],
            "relevance_score": 8,
            "overall_score": 7,
            "feedback_summary": "Tóm tắt đánh giá tổng thể"
        }}
        
        Đảm bảo phản hồi của bạn chỉ chứa JSON hợp lệ, không có văn bản giới thiệu hoặc giải thích.
        """
        
        # Gọi API
        response = await client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là AI Interview Evaluator, một chuyên gia đánh giá câu trả lời phỏng vấn."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
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
                    
            feedback = json.loads(result_text.strip())
            return feedback
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi xử lý JSON: {str(e)}")
            logger.error(f"Dữ liệu nhận được: {result_text}")
            raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
            
    except Exception as e:
        logger.error(f"Lỗi khi phân tích câu trả lời phỏng vấn: {str(e)}")
        raise 