import base64
import binascii
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status

from src.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.root = Path(settings.storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

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
        image_bytes = self._decode_payload(image_b64)
        folder = self.root / student_id
        folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"{prefix}_{timestamp}.jpg"
        path = folder / filename
        path.write_bytes(image_bytes)

        if settings.storage_base_url:
            return f"{settings.storage_base_url.rstrip('/')}/{student_id}/{filename}"
        return str(path.as_posix())


storage_service = StorageService()
