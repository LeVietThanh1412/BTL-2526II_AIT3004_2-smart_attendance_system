import tempfile
from pathlib import Path

import cv2
import numpy as np


class FaceEngine:
    MODEL_NAME = "Facenet512"   # 512-dim, good accuracy/speed tradeoff
    DETECTOR = "retinaface"     # accurate detector

    def __init__(self) -> None:
        try:
            from deepface import DeepFace
            self._deepface = DeepFace
            self.initialized = True
            # Warm-up: trigger model download on first use (lazy)
        except ImportError:
            self._deepface = None
            self.initialized = False
            print("WARNING: deepface not installed. AI features disabled.")

    def get_embedding_from_bytes(self, image_bytes: bytes) -> list[float] | None:
        """Extract face embedding from raw image bytes. Returns None if no face."""
        if not self.initialized:
            return None

        # Write to a temp file because DeepFace expects a file path or numpy array
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            return self._extract(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def get_embedding_from_path(self, image_path: str) -> list[float] | None:
        """Extract face embedding from a local file path."""
        if not self.initialized:
            return None
        return self._extract(image_path)

    def _extract(self, image_path: str) -> list[float] | None:
        try:
            results = self._deepface.represent(
                img_path=image_path,
                model_name=self.MODEL_NAME,
                detector_backend=self.DETECTOR,
                enforce_detection=True,
                align=True,
            )
            if not results:
                return None
            # Take the largest face (by area of facial area)
            best = max(results, key=lambda r: r.get("facial_area", {}).get("w", 0) * r.get("facial_area", {}).get("h", 0))
            emb = best["embedding"]
            # L2-normalize for cosine similarity in Qdrant
            arr = np.array(emb, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr /= norm
            return arr.tolist()
        except Exception as e:
            print(f"[FaceEngine] Extraction error: {e}")
            return None


face_engine = FaceEngine()
EMBEDDING_SIZE = 512   # Facenet512 output dimension
