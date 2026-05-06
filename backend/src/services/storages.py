import logging
import time
import uuid
from io import BytesIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from src.core.config import settings

logger = logging.getLogger(__name__)


class MinioService:
    def __init__(self) -> None:
        self.endpoint = settings.minio_endpoint.strip()
        self.access_key = settings.minio_access_key.strip()
        self.secret_key = settings.minio_secret_key.strip()
        self.bucket_name = settings.minio_bucket.strip()
        self.secure = settings.minio_secure
        self.public_base_url = settings.minio_public_base_url.strip().rstrip("/")

        scheme = "https" if self.secure else "http"
        self.endpoint_url = f"{scheme}://{self.endpoint.lstrip('/')}"

        logger.info("Connecting to MinIO at %s", self.endpoint_url)

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self, max_retries: int = 10, base_delay: float = 2.0) -> None:
        """Check / create the bucket, retrying if MinIO is not ready yet."""
        for attempt in range(1, max_retries + 1):
            try:
                self.client.head_bucket(Bucket=self.bucket_name)
                logger.info("MinIO bucket '%s' is ready.", self.bucket_name)
                return
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code", "")
                if error_code in ("404", "NoSuchBucket"):
                    try:
                        self.client.create_bucket(Bucket=self.bucket_name)
                        logger.info("Created MinIO bucket '%s'.", self.bucket_name)
                        return
                    except (BotoCoreError, ClientError) as create_exc:
                        logger.warning(
                            "Attempt %d/%d - cannot create bucket: %s",
                            attempt,
                            max_retries,
                            create_exc,
                        )
                else:
                    logger.warning(
                        "Attempt %d/%d - MinIO head_bucket error (code=%s): %s",
                        attempt,
                        max_retries,
                        error_code,
                        exc,
                    )
            except Exception as exc:
                logger.warning(
                    "Attempt %d/%d - MinIO not reachable: %s",
                    attempt,
                    max_retries,
                    exc,
                )

            if attempt < max_retries:
                delay = min(base_delay * attempt, 15.0)
                logger.info("Retrying MinIO connection in %.1fs...", delay)
                time.sleep(delay)

        raise RuntimeError(
            f"Could not connect to MinIO at {self.endpoint_url} after {max_retries} attempts."
        )

    def _build_public_url(self, object_name: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{self.bucket_name}/{object_name}"
        return f"{self.endpoint_url}/{self.bucket_name}/{object_name}"

    def _build_presigned_url(self, object_name: str) -> str:
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=3600,
            )
        except (BotoCoreError, ClientError):
            return self._build_public_url(object_name)

    def upload_image(self, file_bytes: bytes, filename: str) -> str:
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file payload.",
            )

        safe_name = (filename or "image.jpg").strip().replace(" ", "_")
        object_name = f"tmp/{uuid.uuid4().hex}_{safe_name}"

        try:
            self.client.upload_fileobj(
                Fileobj=BytesIO(file_bytes),
                Bucket=self.bucket_name,
                Key=object_name,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot upload image to MinIO.",
            ) from exc

        return self._build_presigned_url(object_name)


minio_service = MinioService()

# class MinIOStorageService:
#     def __init__(self) -> None:
#         self.client = Minio(
#             endpoint=settings.minio_endpoint,
#             access_key=settings.minio_access_key,
#             secret_key=settings.minio_secret_key,
#             secure=settings.minio_secure,
#         )
#         self._ensure_bucket()
#
#     def _ensure_bucket(self) -> None:
#         try:
#             if not self.client.bucket_exists(settings.minio_bucket):
#                 self.client.make_bucket(settings.minio_bucket)
#         except S3Error:
#             pass
#
#     @staticmethod
#     def _decode_payload(image_b64: str) -> bytes:
#         payload = image_b64.split(",", 1)[1] if "," in image_b64 else image_b64
#         return base64.b64decode(payload)
#
#     def save_image(self, image_b64: str, student_id: str, prefix: str) -> str:
#         image_bytes = self._decode_payload(image_b64)
#         timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
#         object_name = f"{student_id}/{prefix}_{timestamp}.jpg"
#
#         data = BytesIO(image_bytes)
#         self.client.put_object(
#             bucket_name=settings.minio_bucket,
#             object_name=object_name,
#             data=data,
#             length=len(image_bytes),
#             content_type="image/jpeg",
#         )
#
#         return object_name
#
# storage_service = MinIOStorageService()
