import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database.Base import Base


class AttendanceStatus(str, enum.Enum):
	success = "success"
	failed = "failed"


class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	student_id = Column(String(30), unique=True, index=True, nullable=False)
	name = Column(String(255), nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	embedding = relationship(
		"FaceEmbedding",
		uselist=False,
		back_populates="user",
		cascade="all, delete-orphan",
	)
	attendance_logs = relationship(
		"AttendanceLog",
		back_populates="user",
		cascade="all, delete-orphan",
	)


class FaceEmbedding(Base):
	__tablename__ = "face_embeddings"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
	embedding_vector = Column(Text, nullable=False)
	image_paths = Column(Text, nullable=False, default="[]")
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	user = relationship("User", back_populates="embedding")


class AttendanceLog(Base):
	__tablename__ = "attendance_logs"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	similarity_score = Column(Float, nullable=False)
	status = Column(Enum(AttendanceStatus), nullable=False)
	captured_image_path = Column(String(500), nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

	user = relationship("User", back_populates="attendance_logs")

