from fastapi import FastAPI

from src.api.v1 import api_v1_router
from src.core.config import settings
from src.database import Base, engine
from src.models import AttendanceLog, FaceEmbedding, User


app = FastAPI(
	title=settings.app_name,
	version=settings.app_version,
	debug=settings.debug,
)


@app.on_event("startup")
def on_startup() -> None:
	# Ensure all ORM models are loaded before table creation.
	_ = (User, FaceEmbedding, AttendanceLog)
	Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
	return {"status": "ok"}


app.include_router(api_v1_router, prefix="/api/v1")
