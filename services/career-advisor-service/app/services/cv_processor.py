import os
import json
import logging
import PyPDF2
import docx
from typing import Tuple, Dict, Any, List
from fastapi import UploadFile
import tempfile
from datetime import datetime

from app.services.openai_service import (
    analyze_cv_content,
    analyze_career_profile,
    identify_skill_gaps,
)
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import search_career_pathways

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
    async def analyze_cv(cv_id: int, text: str) -> Dict[str, Any]:
        """
        Phân tích đầy đủ CV bao gồm thông tin nghề nghiệp và đề xuất
        """
        try:
            # 1. Phân tích cơ bản CV
            basic_analysis = analyze_cv_content(text)
            
            # 2. Tạo career profile từ kết quả phân tích
            career_analysis = await analyze_career_profile(
                skills=basic_analysis.get("skills", {}).get("technical", []) +
                       basic_analysis.get("skills", {}).get("soft", []),
                experiences=basic_analysis.get("experience", []),
                education=basic_analysis.get("education", []),
                career_goals=basic_analysis.get("analysis", {}).get("career_recommendations", []),
                preferred_industries=[rec.get("position", "").split()[0] for rec in
                                   basic_analysis.get("analysis", {}).get("career_recommendations", [])]
            )
            
            # 3. Tạo embedding cho CV
            embedding_service = EmbeddingService.get_instance()
            cv_text = f"{text}\n{json.dumps(basic_analysis)}"
            embedding_vector = embedding_service.create_embedding(cv_text)
            
            # 4. Tìm kiếm career recommendations dựa trên vector similarity
            career_matches = search_career_pathways(
                query="",  # Sử dụng vector similarity thay vì query
                embedding_vector=embedding_vector,
                top_k=5
            )
            
            # 5. Phân tích skill gaps cho top career path
            if career_matches:
                top_career = career_matches[0]["name"]
                skill_gaps = await identify_skill_gaps(
                    current_skills=basic_analysis.get("skills", {}).get("technical", []),
                    target_career=top_career
                )
            else:
                skill_gaps = {"error": "Không thể xác định skill gaps"}
            
            # Tổng hợp kết quả
            analysis_result = {
                "cv_analysis": basic_analysis,
                "career_analysis": career_analysis,
                "career_matches": career_matches,
                "skill_gaps": skill_gaps,
                "embedding_vector": embedding_vector,
                "metrics": {
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "sections_found": len(basic_analysis.get("experience", [])) +
                                   len(basic_analysis.get("education", []))
                },
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích CV {cv_id}: {str(e)}")
            return {
                "error": f"Không thể phân tích chi tiết CV: {str(e)}",
                "cv_id": cv_id,
                "basic_analysis": {
                    "content": text[:1000] + "..." if len(text) > 1000 else text,
                    "word_count": len(text.split()),
                    "char_count": len(text)
                }
            }