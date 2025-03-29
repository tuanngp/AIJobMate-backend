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
        
        # Lưu file tạm thời
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            try:
                if file_extension == '.pdf':
                    extracted_text = CVProcessor._extract_from_pdf(temp_file.name)
                elif file_extension == '.docx':
                    extracted_text = CVProcessor._extract_from_docx(temp_file.name)
                else:  # .txt
                    extracted_text = content.decode('utf-8')
            finally:
                os.unlink(temp_file.name)  # Xóa file tạm
                
        return file_name, file_extension[1:], extracted_text
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Trích xuất text từ file PDF"""
        text = ""
        with open(file_path, 'rb') as file:
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
        Phân tích nội dung CV và trích xuất thông tin quan trọng
        Có thể mở rộng thêm để sử dụng AI để phân tích
        """
        # TODO: Implement AI analysis
        return {
            "content": text,
            "word_count": len(text.split()),
            "char_count": len(text)
        }