from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text
from app.db.base_class import Base

class CareerPathway(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Tên hướng đi nghề nghiệp
    description = Column(Text)  # Mô tả chi tiết
    industry = Column(String(255))  # Ngành công nghiệp
    required_skills = Column(JSON)  # Danh sách kỹ năng yêu cầu
    required_experience = Column(Integer)  # Số năm kinh nghiệm yêu cầu
    
    # Thông tin bổ sung
    salary_range_min = Column(Float, nullable=True)  # Mức lương tối thiểu
    salary_range_max = Column(Float, nullable=True)  # Mức lương tối đa
    growth_potential = Column(Float, nullable=True)  # Tiềm năng phát triển (thang điểm 1-10)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)