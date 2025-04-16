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
from datetime import datetime
from functools import partial

from app.services.openai_service import (
    analyze_cv_content,
    analyze_career_profile,
    assess_cv_quality,
    identify_skill_gaps,
)
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import search_career_pathways, store_career_pathway

logger = logging.getLogger(__name__)

class CVProcessor:
    """Service để xử lý và phân tích CV"""
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    
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
            # Tạo và ghi temporary file
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                temp_path = temp_file.name
            
            # Xử lý file theo định dạng
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
        """Trích xuất text từ file PDF"""
        text = ""
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Trích xuất text từ file DOCX"""
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()

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
        """
        Tạo embedding vector cho CV với cơ chế retry và timeout.
        
        Args:
            cv_id: ID của CV
            text: Nội dung CV
            basic_analysis: Kết quả phân tích cơ bản
            
        Returns:
            Optional[List[float]]: Vector embedding hoặc None nếu thất bại
        """
        try:
            # Lấy instance của EmbeddingService
            embedding_service = await wait_for(
                EmbeddingService.get_instance(),
                timeout=10.0
            )
            
            # Chuẩn bị dữ liệu
            cv_text = f"{text}\n{json.dumps(basic_analysis)}"
            
            # Tạo embedding vector với timeout
            embedding_vector = await wait_for(
                embedding_service.create_embedding(cv_text),
                timeout=20.0
            )
            
            # Kiểm tra kết quả là coroutine
            if asyncio.iscoroutine(embedding_vector):
                embedding_vector = await wait_for(embedding_vector, timeout=10.0)
                
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
    async def analyze_cv(cv_id: int, text: str) -> Dict[str, Any]:
        """
        Phân tích đầy đủ CV bao gồm thông tin nghề nghiệp và đề xuất
        """
        try:
            # 1. Phân tích cơ bản CV và validate kết quả
            basic_analysis = await analyze_cv_content(text)
            if hasattr(basic_analysis, '__await__'):
                basic_analysis = await basic_analysis
                
            if not basic_analysis or not isinstance(basic_analysis, dict):
                raise ValueError("Không thể phân tích CV: Kết quả phân tích không hợp lệ")

            # Extract technical và soft skills
            all_skills = []
            skills_data = basic_analysis.get("skills", {})
            if isinstance(skills_data, dict):
                all_skills.extend(skills_data.get("technical", []))
                all_skills.extend(skills_data.get("soft", []))

            # 2. Tạo career profile dựa trên basic analysis
            career_analysis = await analyze_career_profile(
                skills=all_skills,
                experiences=basic_analysis.get("experience", []),
                education=basic_analysis.get("education", []),
                career_goals=basic_analysis.get("career_goals", []),  # Không phụ thuộc vào career_recommendations
                preferred_industries=[]  # Sẽ được xác định sau
            )
            
            # 3. Tạo embedding cho CV với retry mechanism
            try:
                embedding_vector = await wait_for(
                    CVProcessor._create_cv_embedding_with_retry(
                        cv_id=cv_id,
                        text=text,
                        basic_analysis=basic_analysis
                    ),
                    timeout=30.0  # 30 giây timeout cho việc tạo embedding
                )
            except TimeoutError:
                logger.error(f"CV {cv_id}: Timeout khi tạo embedding vector")
                embedding_vector = None
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi tạo embedding vector: {str(e)}")
                embedding_vector = None

            # 4. Xử lý career matches
            career_matches = []

            try:
                # 4.1 Lưu career recommendations vào Pinecone
                basic_analysis_data = basic_analysis.get("analysis", {})
                career_recommendations = basic_analysis_data.get("career_recommendations", [])
                
                if career_recommendations:
                    # Tạo tasks để lưu career pathways
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
                    
                    # Chờ tất cả tasks hoàn thành với timeout
                    try:
                        await wait_for(asyncio.gather(*store_tasks), timeout=20.0)
                    except TimeoutError:
                        logger.warning(f"CV {cv_id}: Timeout khi lưu career pathways")
                    except Exception as e:
                        logger.error(f"CV {cv_id}: Lỗi khi lưu career pathways: {str(e)}")

                # 4.2 Tìm kiếm career matches
                if embedding_vector:
                    try:
                        # Tìm kiếm dựa trên embedding vector với timeout
                        career_matches = await wait_for(
                            search_career_pathways(
                                embedding_vector=embedding_vector,
                                skills=all_skills,
                                top_k=5
                            ),
                            timeout=10.0
                        )
                    except (TimeoutError, Exception) as e:
                        logger.error(f"CV {cv_id}: Lỗi khi tìm career matches từ embedding: {str(e)}")
                        career_matches = []

                # Nếu không có matches từ embedding, sử dụng fallback
                if not career_matches:
                    career_paths = career_analysis.get("career_paths", [])[:5]
                    career_matches = [
                        {"name": path, "score": fit_score}
                        for path, fit_score in career_paths
                    ]

            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi trong quá trình xử lý career matches: {str(e)}")
                # Đảm bảo luôn có career_matches, dù là rỗng
                career_matches = []
            
            # 5. Phân tích skill gaps cho các career matches
            try:
                all_skill_gaps = await identify_skill_gaps(
                    current_skills=all_skills,
                    target_career=career_matches,
                    experience_level=basic_analysis.get("analyst").get("experience_level", "N/A"),
                )
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi phân tích skill gaps: {str(e)}")
                all_skill_gaps = []
            
            # Tổng hợp kết quả với validation
            # Đánh giá chất lượng CV
            try:
                quality_assessment = await assess_cv_quality(text)
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi đánh giá chất lượng CV: {str(e)}")
                quality_assessment = None

            # Tổng hợp kết quả với validation
            analysis_result = {
                "basic_analysis": basic_analysis or {},
                "career_analysis": career_analysis or {},
                "career_matches": career_matches or [],
                "skill_gaps": all_skill_gaps,
                "quality_assessment": quality_assessment or {},
                "embedding_vector": embedding_vector,
            }
            return analysis_result

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