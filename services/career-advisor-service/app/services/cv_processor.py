import os
import json
import logging
import PyPDF2
import docx
import asyncio
from asyncio import TimeoutError, wait_for
from typing import Tuple, Dict, Any, List, Optional
from fastapi import UploadFile
import tempfile
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.openai_service import (
    analyze_cv_content,
    analyze_career_profile,
    assess_cv_quality,
    identify_skill_gaps,
)
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import search_career_pathways, store_career_pathway

# Cấu hình logger
logger = logging.getLogger(__name__)

class CVProcessor:
    """Service để xử lý và phân tích CV"""
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    # Thêm các giá trị mặc định cho phân tích
    DEFAULT_ANALYSIS = {
        "skills": {"technical": [], "soft": []},
        "experience": [],
        "education": [],
        "career_goals": [],
        "analyst": {"experience_level": "Entry"}
    }
    
    @staticmethod
    async def process_cv(file: UploadFile) -> Tuple[str, str, str]:
        """
        Xử lý file CV và trả về tuple gồm (file_name, file_type, extracted_text)
        """
        file_name = file.filename
        file_extension = os.path.splitext(file_name)[1].lower()
        
        if file_extension not in CVProcessor.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Định dạng file không được hỗ trợ. Chỉ hỗ trợ: {', '.join(CVProcessor.ALLOWED_EXTENSIONS)}"
            )
        
        # Reset file position và đọc content
        await file.seek(0)
        content = await file.read()
        
        # Xử lý file dựa trên định dạng
        if file_extension == '.txt':
            text_content = content.decode('utf-8')
            return file_name, file_extension[1:], text_content
            
        # Xử lý PDF và DOCX với temporary file
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            if file_extension == '.pdf':
                with open(temp_path, 'rb') as pdf_file:
                    extracted_text = CVProcessor._extract_from_pdf(pdf_file)
            else:  # .docx
                extracted_text = CVProcessor._extract_from_docx(temp_path)
                
            return file_name, file_extension[1:], extracted_text
            
        except Exception as e:
            logger.error(f"Failed to process file: {str(e)}")
            raise ValueError(f"Lỗi khi xử lý file: {str(e)}")
            
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file: {str(e)}")
    
    @staticmethod
    def _extract_from_pdf(file) -> str:
        """Trích xuất text từ file PDF với xử lý từng trang để giảm sử dụng memory"""
        text_parts = []
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
            
        return "\n".join(text_parts).strip()
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Trích xuất text từ file DOCX"""
        doc = docx.Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: None
    )
    async def _create_cv_embedding_with_retry(
        cv_id: int,
        text: str,
        basic_analysis: Dict[str, Any]
    ) -> Optional[List[float]]:
        """Tạo embedding vector cho CV với cơ chế retry và timeout."""
        try:
            embedding_service = await wait_for(
                EmbeddingService.get_instance(),
                timeout=10.0
            )
            
            # Chuẩn bị dữ liệu - sử dụng nội dung quan trọng để tạo embedding hiệu quả
            important_fields = {
                "skills": basic_analysis.get("skills", {}),
                "experience": basic_analysis.get("experience", []),
                "education": basic_analysis.get("education", []),
                "career_goals": basic_analysis.get("career_goals", []),
            }
            
            cv_text = f"{text}\n{json.dumps(important_fields)}"
            
            # Tạo embedding vector với timeout
            embedding_vector = await wait_for(
                embedding_service.create_embedding(cv_text),
                timeout=20.0
            )
                
            if not isinstance(embedding_vector, (list, tuple)) or not embedding_vector:
                raise ValueError("Embedding vector không hợp lệ")
                
            return embedding_vector
            
        except TimeoutError as e:
            logger.error(f"CV {cv_id}: Timeout khi tạo embedding vector: {str(e)}")
            raise  # Raise để trigger retry
        except Exception as e:
            logger.error(f"CV {cv_id}: Lỗi khi tạo embedding vector: {str(e)}")
            raise  # Raise để trigger retry

    @staticmethod
    async def _extract_skills(basic_analysis: Dict[str, Any]) -> List[str]:
        """Trích xuất danh sách kỹ năng từ basic analysis"""
        all_skills = []
        skills_data = basic_analysis.get("skills", {})
        if isinstance(skills_data, dict):
            all_skills.extend(skills_data.get("technical", []))
            all_skills.extend(skills_data.get("soft", []))
        return all_skills

    @staticmethod
    async def _process_career_matches(
        cv_id: int, 
        embedding_vector: Optional[List[float]], 
        all_skills: List[str],
        career_analysis: Dict[str, Any],
        basic_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Xử lý và lấy career matches từ nhiều nguồn"""
        career_matches = []
        try:
            # Lưu career recommendations vào Pinecone
            basic_analysis_data = basic_analysis.get("analysis", {})
            career_recommendations = basic_analysis_data.get("career_recommendations", [])
            
            if career_recommendations:
                store_tasks = [
                    store_career_pathway(
                        pathway_id=f"career_{rec['position'].lower().replace(' ', '_')}",
                        name=rec['position'],
                        description=rec.get('description', ''),
                        required_skills=rec.get('required_skills', []),
                        reason=rec.get('reason', ''),
                        industry=rec.get('industry', ''),
                        required_experience=rec.get('required_experience', ''),
                        score=rec.get('score', 0.0),
                    )
                    for rec in career_recommendations
                ]
                
                try:
                    await wait_for(asyncio.gather(*store_tasks), timeout=20.0)
                except TimeoutError:
                    logger.warning(f"CV {cv_id}: Timeout khi lưu career pathways")
                except Exception as e:
                    logger.error(f"CV {cv_id}: Lỗi khi lưu career pathways: {str(e)}")

            # Tìm kiếm career matches từ embedding nếu có
            if embedding_vector:
                try:
                    career_matches = await wait_for(
                        search_career_pathways(
                            embedding_vector=embedding_vector,
                            skills=all_skills,
                            top_k=5
                        ),
                        timeout=10.0
                    )
                except Exception as e:
                    logger.error(f"CV {cv_id}: Lỗi khi tìm career matches từ embedding: {str(e)}")

            # Fallback: sử dụng career paths từ career analysis nếu không có matches từ embedding
            if not career_matches:
                career_paths = career_analysis.get("career_paths", [])[:5]
                career_matches = [
                    {"name": path, "score": fit_score}
                    for path, fit_score in career_paths
                ]

        except Exception as e:
            logger.error(f"CV {cv_id}: Lỗi trong quá trình xử lý career matches: {str(e)}")
            
        # Luôn đảm bảo trả về list, dù là rỗng
        return career_matches or []

    @staticmethod
    async def analyze_cv(cv_id: int, text: str) -> Dict[str, Any]:
        """Phân tích đầy đủ CV bao gồm thông tin nghề nghiệp và đề xuất"""
        try:
            # 1. Phân tích cơ bản CV
            basic_analysis = await analyze_cv_content(text)
            
            if not basic_analysis or not isinstance(basic_analysis, dict):
                raise ValueError("Không thể phân tích CV: Kết quả phân tích không hợp lệ")

            # 2. Trích xuất skills
            all_skills = await CVProcessor._extract_skills(basic_analysis)

            # 3. Tạo career profile
            career_analysis = await analyze_career_profile(
                skills=all_skills,
                experiences=basic_analysis.get("experience", []),
                education=basic_analysis.get("education", []),
                career_goals=basic_analysis.get("career_goals", []),
                preferred_industries=[]
            )
            
            # 4. Tạo embedding cho CV
            embedding_vector = None
            try:
                embedding_vector = await wait_for(
                    CVProcessor._create_cv_embedding_with_retry(
                        cv_id=cv_id,
                        text=text,
                        basic_analysis=basic_analysis
                    ),
                    timeout=30.0
                )
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi tạo embedding vector: {str(e)}")

            # 5. Xử lý career matches
            career_matches = await CVProcessor._process_career_matches(
                cv_id=cv_id,
                embedding_vector=embedding_vector,
                all_skills=all_skills,
                career_analysis=career_analysis,
                basic_analysis=basic_analysis
            )
            
            # 6. Phân tích skill gaps
            all_skill_gaps = []
            try:
                experience_level = basic_analysis.get("analyst", {}).get("experience_level", "N/A")
                all_skill_gaps = await identify_skill_gaps(
                    current_skills=all_skills,
                    target_career=career_matches,
                    experience_level=experience_level,
                )
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi phân tích skill gaps: {str(e)}")
            
            # 7. Đánh giá chất lượng CV
            quality_assessment = {}
            try:
                quality_assessment = await assess_cv_quality(text)
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi đánh giá chất lượng CV: {str(e)}")

            # 8. Tổng hợp kết quả
            return {
                "basic_analysis": basic_analysis,
                "career_analysis": career_analysis,
                "career_matches": career_matches,
                "skill_gaps": all_skill_gaps,
                "quality_assessment": quality_assessment,
                "embedding_vector": embedding_vector,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Lỗi khi phân tích CV {cv_id}: {error_msg}")
            
            # Return a standardized error response
            return {
                "error": True,
                "error_message": error_msg,
                "cv_id": cv_id,
                "basic_analysis": {
                    "content": text[:1000] + "..." if len(text) > 1000 else text,
                    "word_count": len(text.split()),
                    "char_count": len(text)
                }
            }