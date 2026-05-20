import os
import tempfile
from typing import Any

import cv2
import numpy as np
import requests
from deepface import DeepFace
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels


class FaceEngine:
    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "face_embeddings")
        self.model_name = os.getenv("DEEPFACE_MODEL_NAME", "Facenet")
        self.detector_backend = os.getenv("FACE_DETECTOR_BACKEND", "mtcnn")
        self.blur_threshold = float(os.getenv("FACE_BLUR_THRESHOLD", "80.0"))
        self.brightness_threshold = float(os.getenv("FACE_BRIGHTNESS_THRESHOLD", "40.0"))

        if qdrant_api_key:
            self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.qdrant = QdrantClient(url=qdrant_url)

    def _validate_image_quality(self, image: np.ndarray) -> None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())

        if blur_score < self.blur_threshold:
            raise ValueError("image_blurry")
        if brightness < self.brightness_threshold:
            raise ValueError("image_too_dark")

    def extract_vector(self, image_url: str) -> list[float]:
        if not image_url:
            raise ValueError("image_url is required")

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_file.flush()
            tmp_path = tmp_file.name

        try:
            image = cv2.imread(tmp_path)
            if image is None:
                raise ValueError("invalid_image")
            self._validate_image_quality(image)
            representations = DeepFace.represent(
                img_path=tmp_path,
                model_name=self.model_name,
                enforce_detection=True,
                detector_backend=self.detector_backend,
                align=True,
            )
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not representations:
            raise ValueError("No face embedding extracted")

        first_representation = representations[0]
        vector = first_representation.get("embedding")
        if not vector:
            raise ValueError("Embedding vector is empty")

        return [float(v) for v in vector]

    def search_qdrant(self, vector: list[float], student_id: str) -> dict[str, Any]:
        if not vector:
            raise ValueError("vector is required")
        if not student_id:
            raise ValueError("student_id is required")

        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="student_id",
                    match=qmodels.MatchValue(value=student_id),
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
            return {"student_id": str(student_id), "score": 0.0, "found": False}

        best_match = results[0]
        payload = best_match.payload or {}
        matched_id = payload.get("student_id") or payload.get("user_id") or student_id

        return {
            "student_id": str(matched_id),
            "score": float(best_match.score or 0.0),
            "found": True,
        }
