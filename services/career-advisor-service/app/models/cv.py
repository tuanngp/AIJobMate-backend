from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from app.db.base_class import Base

class CV(Base):
    # Thông tin về CV
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    file_name = Column(String(255))
    file_type = Column(String(50))
    original_content = Column(Text)
    extracted_text = Column(Text)
    
    # Thông tin profile được trích xuất từ CV
    personal_info = Column(JSON, nullable=True)  # Thông tin cá nhân (name, email, phone, etc.)
    education = Column(JSON, nullable=True)  # List học vấn
    certifications = Column(JSON, nullable=True)  # List chứng chỉ
    experiences = Column(JSON, nullable=True)  # List kinh nghiệm làm việc
    skills = Column(JSON, nullable=True)  # List các kỹ năng
    analysis = Column(JSON, nullable=True)  # List các phân tích khác (nếu có)
    
    # Kết quả phân tích CV
    strengths = Column(JSON, nullable=True)  # List điểm mạnh
    weaknesses = Column(JSON, nullable=True)  # List điểm yếu
    skill_gaps = Column(JSON, nullable=True)  # List kỹ năng cần phát triển
    career_paths = Column(JSON, nullable=True)  # List các con đường sự nghiệp tiềm năng
    recommended_skills = Column(JSON, nullable=True)  # List kỹ năng nên học
    recommended_actions = Column(JSON, nullable=True)  # List hành động đề xuất
    analysis_summary = Column(JSON, nullable=True)  # Tóm tắt phân tích CV    
    
    # Kết quả tìm kiếm nghề nghiệp
    career_matches = Column(JSON, nullable=True) # List các nghề nghiệp phù hợp với CV
    preferred_industries = Column(JSON, nullable=True)  # List ngành nghề ưa thích

    # Vector embedding cho tìm kiếm tương đồng
    embedding_vector = Column(JSON, nullable=True)  # Vector biểu diễn CV
    
    # Đánh giá chất lượng CV
    overall_score = Column(JSON, nullable=True)  # Kết quả đánh giá chất lượng tổng thể
    completeness = Column(JSON, nullable=True) # Đánh giá độ hoàn thiện của CV
    formatting = Column(JSON, nullable=True) # Đánh giá về định dạng và trình bày
    section_scores = Column(JSON, nullable=True) # Đánh giá từng phần của CV (education, experience, etc.)
    language_quality = Column(JSON, nullable=True) # Đánh giá chất lượng ngôn ngữ (grammar, spelling, etc.)
    ats_compatibility = Column(JSON, nullable=True) # Đánh giá khả năng tương thích với ATS (Applicant Tracking System)
    detailed_metrics = Column(JSON, nullable=True) # Các chỉ số chi tiết khác
    improvement_priority = Column(JSON, nullable=True) # Đánh giá mức độ cần cải thiện của CV   
    
    # Trạng thái phân tích
    analysis_status = Column(String(50), nullable=True)  # processing, completed, failed
    analysis_error = Column(Text, nullable=True)  # Lưu lỗi nếu có
    last_analyzed_at = Column(DateTime, nullable=True)  # Thời điểm phân tích gần nhất
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)