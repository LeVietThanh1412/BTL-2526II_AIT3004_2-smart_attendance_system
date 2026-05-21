from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Attendance API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")

    default_camera_id: str = Field(default="cam_01", alias="DEFAULT_CAMERA_ID")
    time_late: str = Field(default="08:00", alias="TIME_LATE")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    mysql_url: str | None = Field(default=None, alias="MYSQL_URL")
    mysql_host: str = Field(default="mysql", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str | None = Field(default=None, alias="MYSQL_DATABASE")
    mysql_user: str | None = Field(default=None, alias="MYSQL_USER")
    mysql_password: str | None = Field(default=None, alias="MYSQL_PASSWORD")

    redis_url: str = Field(alias="REDIS_URL")
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    redis_embedding_ttl_seconds: int = Field(default=86400, alias="REDIS_EMBEDDING_TTL_SECONDS")

    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_collection: str = Field(default="face_embeddings", alias="QDRANT_COLLECTION")

    # MinIO
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="attendance-images", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_public_base_url: str = Field(alias="MINIO_PUBLIC_BASE_URL")

    # Face AI

    deepface_model_name: str = Field(default="ArcFace", alias="DEEPFACE_MODEL_NAME")
    face_similarity_threshold: float = Field(default=0.6, alias="FACE_MATCH_THRESHOLD")

    min_registration_images: int = Field(default=3, alias="MIN_REGISTRATION_IMAGES")
    detection_confidence: float = Field(default=0.5, alias="DETECTION_CONF")

    # Image quality thresholds
    image_blur_threshold: float = Field(default=35.0, alias="IMAGE_BLUR_THRESHOLD")
    image_brightness_min: float = Field(default=40.0, alias="IMAGE_BRIGHTNESS_MIN")
    image_brightness_max: float = Field(default=250.0, alias="IMAGE_BRIGHTNESS_MAX")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


def get_database_url() -> str:
    if settings.database_url:
        return settings.database_url
    if settings.mysql_url:
        return settings.mysql_url
    if settings.mysql_database and settings.mysql_user and settings.mysql_password:
        encoded_user = quote_plus(settings.mysql_user)
        encoded_password = quote_plus(settings.mysql_password)
        return (
            "mysql+pymysql://"
            f"{encoded_user}:{encoded_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
        )
    raise RuntimeError("DATABASE_URL or MYSQL_URL must be set.")
