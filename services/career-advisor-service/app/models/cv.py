from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class CV(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    file_name = Column(String(255))
    file_type = Column(String(50))
    original_content = Column(Text)
    extracted_text = Column(Text)
    
    # Thông tin profile được trích xuất từ CV
    skills = Column(JSON, nullable=True)  # List các kỹ năng
    experiences = Column(JSON, nullable=True)  # List kinh nghiệm làm việc
    education = Column(JSON, nullable=True)  # List học vấn
    career_goals = Column(JSON, nullable=True)  # List mục tiêu nghề nghiệp
    preferred_industries = Column(JSON, nullable=True)  # List ngành nghề ưa thích
    
    # Kết quả phân tích CV
    strengths = Column(JSON, nullable=True)  # List điểm mạnh
    weaknesses = Column(JSON, nullable=True)  # List điểm yếu
    skill_gaps = Column(JSON, nullable=True)  # List kỹ năng cần phát triển
    recommended_career_paths = Column(JSON, nullable=True)  # List nghề nghiệp phù hợp
    recommended_skills = Column(JSON, nullable=True)  # List kỹ năng nên học
    recommended_actions = Column(JSON, nullable=True)  # List hành động đề xuất
    
    # Vector embedding cho tìm kiếm tương đồng
    embedding_vector = Column(JSON, nullable=True)  # Vector biểu diễn CV
    
    # Trạng thái phân tích
    analysis_status = Column(String(50), nullable=True)  # processing, completed, failed
    analysis_error = Column(Text, nullable=True)  # Lưu lỗi nếu có
    analysis_task_id = Column(String(255), nullable=True)  # ID của task phân tích
    last_analyzed_at = Column(DateTime, nullable=True)  # Thời điểm phân tích gần nhất
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship với User model
    user = relationship("User", back_populates="cvs")