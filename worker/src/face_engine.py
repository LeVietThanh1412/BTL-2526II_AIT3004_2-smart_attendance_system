import logging
import os
import tempfile
from typing import Any

import cv2
import numpy as np
import requests
from deepface import DeepFace
from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

logger = logging.getLogger(__name__)


class FaceEngine:
    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "face_embeddings")
        self.model_name = os.getenv("DEEPFACE_MODEL_NAME", "Facenet")
        self.detector_backend = os.getenv("DETECTOR_BACKEND", "mtcnn")

        # Configurable thresholds
        self.match_threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
        self.detection_conf = float(os.getenv("DETECTION_CONF", "0.5"))
        self.blur_threshold = float(os.getenv("IMAGE_BLUR_THRESHOLD", "35.0"))
        self.brightness_min = float(os.getenv("IMAGE_BRIGHTNESS_MIN", "40.0"))
        self.brightness_max = float(os.getenv("IMAGE_BRIGHTNESS_MAX", "250.0"))

        if qdrant_api_key:
            self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.qdrant = QdrantClient(url=qdrant_url)

    def check_image_quality(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Check image quality: blur detection and brightness validation.

        Kiem tra chat luong anh: do mo va do sang.

        Args:
            image_bytes: Raw image bytes

        Returns:
            dict with 'ok' (bool) and 'reason' (str) if not ok
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {"ok": False, "reason": "Không thể đọc ảnh. Định dạng không hợp lệ."}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check blur using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < self.blur_threshold:
            logger.warning("Image too blurry: laplacian_var=%.2f < threshold=%.2f", laplacian_var, self.blur_threshold)
            return {
                "ok": False,
                "reason": f"Ảnh quá mờ (blur score: {laplacian_var:.1f}, ngưỡng: {self.blur_threshold:.1f}). Vui lòng chụp lại rõ nét hơn.",
            }

        # Check brightness
        mean_brightness = float(np.mean(gray))
        if mean_brightness < self.brightness_min:
            logger.warning("Image too dark: brightness=%.2f < min=%.2f", mean_brightness, self.brightness_min)
            return {
                "ok": False,
                "reason": f"Ảnh quá tối (brightness: {mean_brightness:.1f}, tối thiểu: {self.brightness_min:.1f}). Vui lòng chụp ở nơi sáng hơn.",
            }
        if mean_brightness > self.brightness_max:
            logger.warning("Image too bright: brightness=%.2f > max=%.2f", mean_brightness, self.brightness_max)
            return {
                "ok": False,
                "reason": f"Ảnh quá sáng (brightness: {mean_brightness:.1f}, tối đa: {self.brightness_max:.1f}). Vui lòng giảm độ sáng.",
            }

        return {"ok": True}

    def extract_vector(self, image_url: str) -> list[float]:
        """
        Download image, check quality, detect + align face, and extract embedding.

        Tai anh, kiem tra chat luong, detect + align khuon mat, va trich xuat embedding.

        Args:
            image_url: URL of the image in MinIO

        Returns:
            Face embedding vector as list of floats

        Raises:
            ValueError: If image quality is bad or no face detected
        """
        if not image_url:
            raise ValueError("image_url is required")

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        image_bytes = response.content

        # Check image quality before processing
        quality = self.check_image_quality(image_bytes)
        if not quality["ok"]:
            raise ValueError(quality["reason"])

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file.flush()
            tmp_path = tmp_file.name

        try:
            representations = DeepFace.represent(
                img_path=tmp_path,
                model_name=self.model_name,
                enforce_detection=True,
                detector_backend=self.detector_backend,
                align=True,
            )
        except ValueError as exc:
            # DeepFace raises ValueError when no face is detected
            raise ValueError(f"Không phát hiện khuôn mặt trong ảnh: {exc}") from exc
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not representations:
            raise ValueError("Không trích xuất được embedding khuôn mặt.")

        first_representation = representations[0]

        # Check detection confidence if available
        face_confidence = first_representation.get("face_confidence", 1.0)
        if face_confidence < self.detection_conf:
            raise ValueError(
                f"Độ tin cậy phát hiện khuôn mặt quá thấp ({face_confidence:.2f} < {self.detection_conf:.2f}). "
                "Vui lòng chụp rõ mặt hơn."
            )

        vector = first_representation.get("embedding")
        if not vector:
            raise ValueError("Embedding vector is empty")

        return [float(v) for v in vector]

    def search_qdrant(self, vector: list[float], student_id: str) -> dict[str, Any]:
        """
        Search Qdrant for matching face vectors, filtered by student_id.

        Tim kiem vector khuon mat khop trong Qdrant, loc theo student_id.

        Args:
            vector: Face embedding vector to match against
            student_id: Student ID to filter search results

        Returns:
            dict with 'student_id', 'score', 'matched', 'reason'
        """
        if not vector:
            raise ValueError("vector is required")
        if not student_id:
            raise ValueError("student_id is required")

        # Filter Qdrant search to only vectors belonging to this student
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="student_id",
                    match=MatchValue(value=student_id),
                )
            ]
        )

        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=1,
            with_payload=True,
        )

        if not results:
            logger.warning("No vectors found for student_id=%s in Qdrant", student_id)
            return {
                "student_id": student_id,
                "score": 0.0,
                "matched": False,
                "reason": f"Không tìm thấy vector khuôn mặt cho sinh viên '{student_id}'.",
            }

        best_match = results[0]
        score = float(best_match.score or 0.0)
        matched = score > self.match_threshold

        if matched:
            reason = f"Nhận diện thành công (similarity: {score:.4f} > threshold: {self.match_threshold:.4f})."
        else:
            reason = (
                f"Khuôn mặt không khớp với sinh viên '{student_id}' "
                f"(similarity: {score:.4f} ≤ threshold: {self.match_threshold:.4f})."
            )

        logger.info(
            "Qdrant search result: student_id=%s, score=%.4f, threshold=%.4f, matched=%s",
            student_id, score, self.match_threshold, matched,
        )

        return {
            "student_id": student_id,
            "score": score,
            "matched": matched,
            "reason": reason,
        }
