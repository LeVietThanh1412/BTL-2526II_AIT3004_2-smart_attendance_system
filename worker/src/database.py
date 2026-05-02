from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
import enum
from src.config import settings

engine = create_engine(settings.MYSQL_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AttendanceStatus(str, enum.Enum):
	success = "success"
	failed = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)
    embedding_vector = Column(String(5000), nullable=False)
    image_paths = Column(String(5000), nullable=False, default="[]")

class AttendanceLog(Base):
	__tablename__ = "attendance_logs"
	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, nullable=False, index=True)
	similarity_score = Column(Float, nullable=False)
	status = Column(Enum(AttendanceStatus), nullable=False)
	minio_image_url = Column(String(500), nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
