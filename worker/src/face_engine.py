import os
import tempfile
from typing import Any

import requests
from deepface import DeepFace
from qdrant_client import QdrantClient


class FaceEngine:
    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "face_embeddings")
        self.model_name = os.getenv("DEEPFACE_MODEL_NAME", "Facenet")

        if qdrant_api_key:
            self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.qdrant = QdrantClient(url=qdrant_url)

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
            representations = DeepFace.represent(
                img_path=tmp_path,
                model_name=self.model_name,
                enforce_detection=False,
                detector_backend="opencv",
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

    def search_qdrant(self, vector: list[float]) -> dict[str, Any]:
        if not vector:
            raise ValueError("vector is required")

        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=1,
            with_payload=True,
        )

        if not results:
            return {"student_id": "Unknown", "score": 0.0}

        best_match = results[0]
        payload = best_match.payload or {}
        student_id = payload.get("student_id") or payload.get("user_id") or "Unknown"

        return {
            "student_id": str(student_id),
            "score": float(best_match.score or 0.0),
        }
