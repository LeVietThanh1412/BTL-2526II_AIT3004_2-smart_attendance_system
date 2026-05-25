from sqlalchemy import Column, DateTime, Integer, String, Boolean
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

from src.database.Base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(30), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_approved = Column(Boolean, default=False)

    name = synonym("full_name")

    embedding = relationship(
        "FaceEmbedding",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    attendances = relationship(
        "Attendance",
        back_populates="user",
        passive_deletes=True,
    )
    schedules = relationship(
        "StudentSchedule",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    attendance_logs = synonym("attendances")

