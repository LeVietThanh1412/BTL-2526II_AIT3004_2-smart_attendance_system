from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Attendance API"
    app_version: str = "1.0.0"
    debug: bool = False

    mysql_url: str = "mysql+pymysql://root:root@localhost:3306/attendance_db"
    redis_url: str = "redis://localhost:6379/0"

    redis_embedding_ttl_seconds: int = 86400

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "attendance-images"
    minio_secure: bool = False

    # Face AI
    face_similarity_threshold: float = 0.6
    min_registration_images: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
