from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	app_name: str = "Smart Attendance API"
	app_version: str = "1.0.0"
	debug: bool = False

	mysql_url: str = "mysql+pymysql://root:root@localhost:3306/attendance_db"
	redis_url: str = "redis://localhost:6379/0"

	storage_root: str = "storage"
	storage_base_url: str = ""

	yolo_model_path: str = "models/yolov8n-face.pt"
	face_similarity_threshold: float = 0.6
	min_registration_images: int = 3

	redis_embedding_ttl_seconds: int = 86400

	# Thêm cấu hình Celery, Qdrant, MinIO theo Phase 1
	celery_broker_url: str = "redis://localhost:6379/0"
	celery_result_backend: str = "redis://localhost:6379/1"

	qdrant_url: str = "http://localhost:6333"

	minio_endpoint: str = "localhost:9000"
	minio_access_key: str = "minioadmin"
	minio_secret_key: str = "minioadmin"
	minio_bucket_name: str = "attendance-images"
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
	)


settings = Settings()
