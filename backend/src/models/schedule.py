from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.Base import Base

class StudentSchedule(Base):
    __tablename__ = "student_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False, index=True) # 0: Monday, 6: Sunday
    shifts = Column(String(50), nullable=False) # e.g. "1,2,3"
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True) # Current active schedule (whether pending or approved)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="schedules")
