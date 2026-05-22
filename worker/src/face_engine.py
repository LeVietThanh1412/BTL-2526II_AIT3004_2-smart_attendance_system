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

        self.model_name = os.getenv("DEEPFACE_MODEL_NAME", "ArcFace")
        self.detector_backend = os.getenv("FACE_DETECTOR_BACKEND", "mtcnn")
        self.detection_conf = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
        self.match_threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))

        if qdrant_api_key:
            self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.qdrant = QdrantClient(url=qdrant_url)

    def check_image_quality(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Check image quality: basic validation only.

        Kiểm tra chất lượng ảnh: chỉ xác thực ảnh đọc được.

        Args:
            image_bytes: Raw image bytes

        Returns:
            dict with 'ok' (bool) and 'reason' (str) if not ok
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {"ok": False, "reason": "Không thể đọc ảnh. Định dạng không hợp lệ."}

        return {"ok": True}

    def extract_vector(self, image_url: str) -> list[float]:
        """
        Download image, check quality, detect + align face, and extract embedding.

        Tải ảnh, kiểm tra chất lượng, phát hiện + căn chỉnh khuôn mặt, và trích xuất embedding.

        Args:
            image_url: URL of the image in MinIO

        Returns:
            Face embedding vector as list of floats

        Raises:
            ValueError: If image quality is bad or no face detected
        """
        if not image_url:
            raise ValueError("Thiếu đường dẫn ảnh.")

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
            raise ValueError("Vector embedding trống.")

        return [float(v) for v in vector]

    def search_qdrant(self, vector: list[float], student_id: str) -> dict[str, Any]:
        """
        Search Qdrant for matching face vectors, filtered by student_id.

        Tìm kiếm vector khuôn mặt khớp trong Qdrant, lọc theo student_id.

        Args:
            vector: Face embedding vector to match against
            student_id: Student ID to filter search results

        Returns:
            dict with 'student_id', 'score', 'matched', 'reason'
        """
        if not vector:
            raise ValueError("Thiếu vector khuôn mặt.")
        if not student_id:
            raise ValueError("Thiếu mã sinh viên.")

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

