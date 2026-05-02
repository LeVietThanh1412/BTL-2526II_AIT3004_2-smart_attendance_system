import base64
import binascii
from datetime import datetime

from fastapi import HTTPException, status
from minio import Minio
from minio.error import S3Error

from src.core.config import settings


class MinIOStorageService:
    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(settings.minio_bucket_name):
                self.client.make_bucket(settings.minio_bucket_name)
        except S3Error:
            pass  # Bucket may already exist or MinIO not ready yet; handled at upload time

    @staticmethod
    def _decode_payload(image_b64: str) -> bytes:
        payload = image_b64.split(",", 1)[1] if "," in image_b64 else image_b64
        try:
            return base64.b64decode(payload)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image payload.",
            ) from exc

    def save_image(self, image_b64: str, student_id: str, prefix: str) -> str:
        """Upload image to MinIO and return the object name (path)."""
        image_bytes = self._decode_payload(image_b64)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        object_name = f"{student_id}/{prefix}_{timestamp}.jpg"

        from io import BytesIO
        data = BytesIO(image_bytes)

        try:
            self.client.put_object(
                bucket_name=settings.minio_bucket_name,
                object_name=object_name,
                data=data,
                length=len(image_bytes),
                content_type="image/jpeg",
            )
        except S3Error as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service error: {exc}",
            ) from exc

        return object_name

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Return a presigned URL valid for `expires_seconds`."""
        from datetime import timedelta
        try:
            return self.client.presigned_get_object(
                bucket_name=settings.minio_bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_seconds),
            )
        except S3Error:
            return object_name

    def download_bytes(self, object_name: str) -> bytes:
        """Download object from MinIO and return raw bytes."""
        try:
            response = self.client.get_object(settings.minio_bucket_name, object_name)
            return response.read()
        except S3Error as exc:
            raise RuntimeError(f"Cannot download {object_name}: {exc}") from exc


storage_service = MinIOStorageService()
