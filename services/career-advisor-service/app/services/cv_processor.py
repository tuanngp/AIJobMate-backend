import os
import json
import logging
import PyPDF2
import docx
import asyncio
from typing import Tuple, Dict, Any, List, Optional
from fastapi import UploadFile
import tempfile
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

from app.services.openai_service import (
    analyze_cv_content,
    analyze_career_profile,
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
        retry_error_callback=lambda retry_state: None  # Trả về None nếu tất cả retry đều thất bại
    )
    async def _create_cv_embedding_with_retry(
        cv_id: int,
        text: str,
        basic_analysis: Dict[str, Any]
    ) -> Optional[List[float]]:
        """
        Tạo embedding vector cho CV với cơ chế retry.
        
        Args:
            cv_id: ID của CV
            text: Nội dung CV
            basic_analysis: Kết quả phân tích cơ bản
            
        Returns:
            Optional[List[float]]: Vector embedding hoặc None nếu thất bại
        """
        try:
            # Lấy instance của EmbeddingService
            embedding_service = await EmbeddingService.get_instance()
            cv_text = f"{text}\n{json.dumps(basic_analysis)}"
            
            # Tạo embedding vector
            embedding_vector = await embedding_service.create_embedding(cv_text)
            
            # Đảm bảo kết quả không phải coroutine
            if hasattr(embedding_vector, '__await__'):
                embedding_vector = await embedding_vector
                
            logger.info(f"CV {cv_id}: Tạo embedding vector thành công")
            return embedding_vector
        except Exception as e:
            logger.warning(f"CV {cv_id}: Lần thử tạo embedding thất bại: {str(e)}")
            raise  # Raise exception để trigger retry

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

            logger.info(f"CV {cv_id}: Phân tích cơ bản hoàn thành. Tìm thấy {len(all_skills)} kỹ năng")

            # 2. Tạo career profile dựa trên basic analysis
            logger.info(f"CV {cv_id}: Bắt đầu phân tích career profile")
            career_analysis = await analyze_career_profile(
                skills=all_skills,
                experiences=basic_analysis.get("experience", []),
                education=basic_analysis.get("education", []),
                career_goals=[],  # Không phụ thuộc vào career_recommendations
                preferred_industries=[]  # Sẽ được xác định sau
            )
            
            # 3. Tạo embedding cho CV
            logger.info(f"CV {cv_id}: Phân tích career profile hoàn thành")

            # 3. Tạo embedding cho CV với retry mechanism
            logger.info(f"CV {cv_id}: Bắt đầu tạo embedding vector")
            embedding_vector = await CVProcessor._create_cv_embedding_with_retry(
                cv_id=cv_id,
                text=text,
                basic_analysis=basic_analysis
            )

            # 4. Tìm kiếm career matches dựa trên embedding hoặc career analysis
            logger.info(f"CV {cv_id}: Bắt đầu tìm kiếm career matches")
            career_matches = []

            # Lưu career recommendations vào Pinecone
            try:
                basic_analysis_data = basic_analysis.get("analysis", {})
                career_recommendations = basic_analysis_data.get("career_recommendations", [])
                
                # Xử lý tất cả career pathways cùng lúc
                career_pathway_tasks = []
                for rec in career_recommendations:
                    pathway_id = f"career_{rec['position'].lower().replace(' ', '_')}"
                    task = store_career_pathway(
                        pathway_id=pathway_id,
                        name=rec['position'],
                        description=rec.get('reason', ''),
                        required_skills=rec.get('required_skills', []),
                        reason=rec.get('reason', ''),
                        score=0.8
                    )
                    career_pathway_tasks.append((pathway_id, task))
                
                # Chờ tất cả tasks hoàn thành
                for pathway_id, task in career_pathway_tasks:
                    try:
                        await task
                        logger.info(f"Đã lưu thành công career pathway {pathway_id}")
                    except Exception as e:
                        logger.error(f"Lỗi khi lưu career pathway {pathway_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Lỗi khi xử lý career pathways: {str(e)}")
                if embedding_vector:
                    # Tìm kiếm dựa trên embedding vector
                    career_matches = await search_career_pathways(
                        embedding_vector=embedding_vector,
                        skills=all_skills,
                        top_k=5
                    )
                    # Đảm bảo career_matches không phải là coroutine
                    if hasattr(career_matches, '__await__'):
                        career_matches = await career_matches
                        
                    logger.info(f"CV {cv_id}: Tìm thấy {len(career_matches)} career matches từ embedding")
                else:
                    # Sử dụng career paths từ career analysis làm fallback
                    career_paths = career_analysis.get("career_paths", [])[:5]
                    career_matches = [
                        {"name": path, "score": 0.8}  # Score mặc định cho non-embedding matches
                        for path in career_paths
                    ]
                    logger.info(f"CV {cv_id}: Sử dụng {len(career_matches)} career matches từ career analysis")
            except Exception as e:
                logger.error(f"CV {cv_id}: Lỗi khi tìm career matches: {str(e)}")

            # 5. Phân tích skill gaps cho các career matches
            logger.info(f"CV {cv_id}: Bắt đầu phân tích skill gaps")
            all_skill_gaps = []
            
            if career_matches and all_skills:
                for match in career_matches[:3]:  # Chỉ phân tích top 3 careers
                    try:
                        career_name = match.get("name")
                        if career_name:
                            logger.info(f"CV {cv_id}: Phân tích skill gaps cho career: {career_name}")
                            gaps = await identify_skill_gaps(
                                current_skills=all_skills,
                                target_career=career_name
                            )
                            if isinstance(gaps, dict) and "missing_skills" in gaps:
                                all_skill_gaps.append({
                                    "career": career_name,
                                    "match_score": match.get("score", 0.0),
                                    "missing_skills": gaps["missing_skills"],
                                    "priority_level": min(len(gaps["missing_skills"]), 10),
                                    "development_time": "3-6 months" if len(gaps["missing_skills"]) <= 5 else "6-12 months"
                                })
                                logger.info(f"CV {cv_id}: Tìm thấy {len(gaps['missing_skills'])} skill gaps cho {career_name}")
                    except Exception as e:
                        logger.warning(f"CV {cv_id}: Lỗi khi phân tích skill gaps cho {career_name}: {str(e)}")
                        continue

            # Validate và standardize career_analysis
            if not isinstance(career_analysis, dict):
                career_analysis = {}
            
            # Tổng hợp kết quả với validation
            analysis_result = {
                "basic_analysis": {
                    "personal_info": basic_analysis.get("personal_info", {}),
                    "education": basic_analysis.get("education", []),
                    "experience": basic_analysis.get("experience", []),
                    "skills": basic_analysis.get("skills", {"technical": [], "soft": [], "languages": []}),
                    "certifications": basic_analysis.get("certifications", [])
                },
                "career_analysis": {
                    "strengths": career_analysis.get("strengths", []),
                    "weaknesses": career_analysis.get("weaknesses", []),
                    "career_paths": career_analysis.get("career_paths", []),
                    "recommended_actions": career_analysis.get("recommended_actions", [])
                },
                "career_matches": career_matches or [],
                "skill_gaps": all_skill_gaps,
                "metrics": {
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "sections_found": len(basic_analysis.get("experience", [])) +
                                   len(basic_analysis.get("education", []))
                },
                "embedding_vector": embedding_vector,
                "analyzed_at": datetime.utcnow().isoformat()
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
                },
                "analyzed_at": datetime.utcnow().isoformat()
            }