from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import api_v1_router
from src.core.config import settings
from src.database import Base, engine
from src.models import AttendanceLog, FaceEmbedding, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo MySQL
    _ = (User, FaceEmbedding, AttendanceLog)
    Base.metadata.create_all(bind=engine)
    
    # Khởi tạo Qdrant ngay từ đầu thay vì đợi tương tác
    try:
        from src.core.qdrant_client import ensure_qdrant_collection
        vector_size = 512 if settings.deepface_model_name in ["ArcFace", "Facenet512"] else 128
        ensure_qdrant_collection(vector_size=vector_size)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi khởi tạo Qdrant: {e}")

    # Cập nhật schema tự động (Auto Migration cho bản cũ)
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE student_schedules ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;"))
            import logging
            logging.getLogger(__name__).info("Đã thêm cột is_approved vào student_schedules.")
    except Exception as e:
        pass # Bỏ qua nếu cột đã tồn tại


    # Khởi động daily scheduler quét điểm danh
    from src.core.scheduler import start_scheduler
    start_scheduler()

    yield


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
