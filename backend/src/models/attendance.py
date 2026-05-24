import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
from src.database.Base import Base

class AttendanceStatus(str, enum.Enum):
    success = "success"
    unknown = "unknown"
    failed = "failed"

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    check_in_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    camera_id = Column(String(50), nullable=False)
    status = Column(Enum(AttendanceStatus, name="attendance_status"), nullable=False)
    is_late_override = Column(Boolean, nullable=True)
    override_reason = Column(String(255), nullable=True)

    similarity_score = synonym("confidence_score")

    user = relationship("User", back_populates="attendances")

    @property
    def timestamp(self):
        return self.check_in_time

    @timestamp.setter
    def timestamp(self, value) -> None:
        self.check_in_time = value

    @property
    def captured_image_path(self):
        return None

    @captured_image_path.setter
    def captured_image_path(self, value) -> None:
        _ = value

AttendanceLog = Attendance