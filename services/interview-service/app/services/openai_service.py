import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from functools import wraps

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings

# ✅ Thêm import từ hệ thống prompt
from app.prompts.prompt_factory import get_prompt_by_domain

# Cấu hình logging
logger = logging.getLogger(__name__)

# Khởi tạo OpenAI client với OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

# Cấu hình headers cho OpenRouter
extra_headers = {
    "HTTP-Referer": settings.SITE_URL,
    "X-Title": settings.SITE_NAME,
    "Content-Type": "application/json"
}

def with_timeout(timeout_seconds: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise Exception(f"Operation timed out after {timeout_seconds} seconds")
        return wrapper
    return decorator

# ✅ Hàm tạo câu hỏi phỏng vấn với prompt theo domain
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=60)
async def generate_interview_questions(
    job_title: str,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    num_questions: int = 5,
    difficulty_level: str = "medium",
    interview_type: str = "mixed",
    skills_required: Optional[List[str]] = None,
    domain: str = "tech"  # ✅ Mặc định là "tech", có thể thay đổi theo use-case
) -> List[Dict[str, Any]]:
    try:
        prompt_provider = get_prompt_by_domain(domain)
        system_prompt = "Bạn là AI Interview Assistant, một hệ thống tạo ra các câu hỏi phỏng vấn thông minh và đánh giá câu trả lời."
        user_prompt = prompt_provider.get_prompt_for_question_generation().format(
            job_title=job_title,
            job_description=job_description or "Không có thông tin",
            industry=industry or "Không có thông tin",
            num_questions=num_questions,
            difficulty_level=difficulty_level,
            interview_type=interview_type,
            skills=", ".join(skills_required) if skills_required else "Không có thông tin cụ thể"
        )

        response = await client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )

        result_text = response.choices[0].message.content.strip()

        # Làm sạch JSON
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "", 1).split("```")[0]
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "", 1).split("```")[0]

        return json.loads(result_text.strip())

    except json.JSONDecodeError as e:
        logger.error(f"Lỗi xử lý JSON: {str(e)}")
        logger.error(f"Dữ liệu nhận được: {result_text}")
        raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
    except Exception as e:
        logger.error(f"Lỗi khi tạo câu hỏi phỏng vấn: {str(e)}")
        raise

# ✅ Hàm đánh giá câu trả lời
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
@with_timeout(timeout_seconds=45)
async def analyze_interview_answer(
    question: str,
    question_type: str,
    user_answer: str,
    job_title: str,
    domain: str = "tech"  # ✅ Cho phép chọn prompt phù hợp
) -> Dict[str, Any]:
    try:
        prompt_provider = get_prompt_by_domain(domain)
        system_prompt = "Bạn là AI Interview Evaluator, một chuyên gia đánh giá câu trả lời phỏng vấn."
        user_prompt = prompt_provider.get_prompt_for_answer_evaluation().format(
            question_type=question_type,
            question=question,
            user_answer=user_answer,
            job_title=job_title
        )

        response = await client.chat.completions.create(
            extra_headers=extra_headers,
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=1500
        )

        result_text = response.choices[0].message.content.strip()

        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "", 1).split("```")[0]
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "", 1).split("```")[0]

        return json.loads(result_text.strip())

    except json.JSONDecodeError as e:
        logger.error(f"Lỗi xử lý JSON: {str(e)}")
        logger.error(f"Dữ liệu nhận được: {result_text}")
        raise Exception("Không thể phân tích phản hồi từ AI. Vui lòng thử lại.")
    except Exception as e:
        logger.error(f"Lỗi khi phân tích câu trả lời phỏng vấn: {str(e)}")
        raise
