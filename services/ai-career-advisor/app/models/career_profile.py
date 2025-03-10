from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Thông tin chung
    title = Column(String, index=True)
    description = Column(Text)
    
    # Thông tin phân tích
    strengths = Column(String)             # Điểm mạnh (JSON)
    weaknesses = Column(String)            # Điểm yếu (JSON)
    skill_gaps = Column(String)            # Thiếu hụt kỹ năng (JSON)
    
    # Thông tin khuyến nghị
    recommended_career_paths = Column(String)  # Hướng phát triển nghề nghiệp được khuyến nghị (JSON)
    recommended_skills = Column(String)        # Kỹ năng được khuyến nghị học (JSON)
    recommended_actions = Column(String)       # Hành động được khuyến nghị thực hiện (JSON)
    
    # Vector embedding cho tìm kiếm semantic
    embedding_vector = Column(String)     # Vector embedding dạng JSON để lưu trong DB
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="career_profiles")


class CareerPathway(Base):
    __tablename__ = "career_pathways"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(Text)
    industry = Column(String, index=True)
    
    # Thông tin chi tiết
    required_skills = Column(String)            # Kỹ năng yêu cầu (JSON)
    required_experience = Column(Integer)       # Kinh nghiệm yêu cầu (năm)
    salary_range_min = Column(Float)            # Lương tối thiểu
    salary_range_max = Column(Float)            # Lương tối đa
    growth_potential = Column(Float)            # Tiềm năng phát triển (1-10)
    
    # Vector embedding
    embedding_vector = Column(String)          # Vector embedding dạng JSON
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 