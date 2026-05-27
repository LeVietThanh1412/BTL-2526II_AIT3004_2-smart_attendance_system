from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from src.api.v1 import api_v1_router
from src.core.config import settings
from src.database import Base, engine
from src.models import AttendanceLog, FaceEmbedding, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    lock_name = "smart_attendance_init"
    lock_acquired = False

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT GET_LOCK(:name, :timeout)"),
                {"name": lock_name, "timeout": 10},
            )
            lock_acquired = result.scalar() == 1

        if lock_acquired:
            # Khởi tạo MySQL (chỉ chạy 1 worker để tránh DDL concurrent)
            _ = (User, FaceEmbedding, AttendanceLog)
            Base.metadata.create_all(bind=engine)

            # Khởi tạo Qdrant ngay từ đầu thay vì đợi tương tác
            try:
                from src.core.qdrant_client import ensure_qdrant_collection

                vector_size = 512 if settings.deepface_model_name in ["ArcFace", "Facenet512"] else 128
                ensure_qdrant_collection(vector_size=vector_size)
            except Exception as e:
                logger.error(f"Lỗi khởi tạo Qdrant: {e}")

            # Cập nhật schema tự động (Auto Migration cho bản cũ)
            try:
                with engine.begin() as conn:
                    try:
                        conn.execute(text("ALTER TABLE student_schedules ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("ALTER TABLE student_schedules ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("ALTER TABLE student_schedules ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("ALTER TABLE student_schedules ADD COLUMN approved_at DATETIME NULL;"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("ALTER TABLE attendances ADD COLUMN snapshot_student_id VARCHAR(30) NULL;"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("ALTER TABLE attendances ADD COLUMN snapshot_full_name VARCHAR(255) NULL;"))
                    except Exception:
                        pass
            except Exception:
                pass

            # Khởi động daily scheduler quét điểm danh (1 instance)
            from src.core.scheduler import start_scheduler

            start_scheduler()
        else:
            logger.info("Skip init: DB lock not acquired.")

        yield
    finally:
        if lock_acquired:
            try:
                with engine.begin() as conn:
                    conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
            except Exception as e:
                logger.warning(f"Release DB lock failed: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "version": settings.app_version}


app.include_router(api_v1_router, prefix="/api/v1")
