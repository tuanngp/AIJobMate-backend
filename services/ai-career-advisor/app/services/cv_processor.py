import os
import PyPDF2
import docx
from typing import Tuple
from fastapi import UploadFile
import tempfile

class CVProcessor:
    """Service để xử lý CV với nhiều định dạng khác nhau"""
    
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
        
        content = await file.read()
        
        # Xử lý file dựa trên định dạng
        if file_extension == '.txt':
            return file_name, file_extension[1:], content.decode('utf-8')
            
        # Xử lý PDF và DOCX với temporary file
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            if file_extension == '.pdf':
                with open(temp_path, 'rb') as pdf_file:
                    extracted_text = CVProcessor._extract_from_pdf(pdf_file)
            else:  # .docx
                extracted_text = CVProcessor._extract_from_docx(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                # Bỏ qua lỗi nếu file đã bị xóa hoặc không thể xóa
                pass
                
        return file_name, file_extension[1:], extracted_text
    
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
    def analyze_cv(text: str) -> dict:
        """
        Phân tích nội dung CV và trích xuất thông tin quan trọng sử dụng AI
        """
        from app.services.openai_service import analyze_cv_content
        
        try:
            # Chuẩn hóa text trước khi phân tích
            normalized_text = text.strip()
            
            # Gọi OpenAI service để phân tích CV
            analysis_result = analyze_cv_content(normalized_text)
            
            # Thêm các metrics cơ bản
            analysis_result["metrics"] = {
                "word_count": len(text.split()),
                "char_count": len(text),
                "sections_found": len(analysis_result.get("experience", [])) +
                                len(analysis_result.get("education", []))
            }
            
            return analysis_result
            
        except Exception as e:
            # Log lỗi và trả về kết quả phân tích cơ bản nếu AI fails
            logger.error(f"Lỗi khi phân tích CV với AI: {str(e)}")
            return {
                "error": "Không thể phân tích chi tiết CV",
                "basic_analysis": {
                    "content": text[:1000] + "..." if len(text) > 1000 else text,
                    "word_count": len(text.split()),
                    "char_count": len(text)
                }
            }