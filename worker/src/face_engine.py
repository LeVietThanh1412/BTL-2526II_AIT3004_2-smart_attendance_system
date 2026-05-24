import os
import tempfile
from typing import Any
import cv2
import numpy as np
import requests
from deepface import DeepFace
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

# Client khởi tạo 1 lần duy nhất để tối ưu hiệu suất
_qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))

class FaceEngine:
    def __init__(self) -> None:
        self.qdrant = _qdrant_client
        self.collection_name = os.getenv("QDRANT_COLLECTION", "face_embeddings")
        self.model_name = os.getenv("DEEPFACE_MODEL_NAME", "ArcFace")
        

        self.vector_size = 512 if self.model_name in ["ArcFace", "Facenet512"] else 128
        
        self.detector_backend = os.getenv("FACE_DETECTOR_BACKEND", "mtcnn")
        self.detection_conf = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
        self.match_threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
        
        self._check_and_init_collection()

    def _check_and_init_collection(self):
        try:
            collections = self.qdrant.get_collections().collections
            target = next((c for c in collections if c.name == self.collection_name), None)
            
            if target:
                info = self.qdrant.get_collection(self.collection_name)
                if info.config.params.vectors.size != self.vector_size:
                    self.qdrant.delete_collection(self.collection_name)
                    self._create_collection()
            else:
                self._create_collection()
        except Exception:
            pass

    def _create_collection(self):
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
        )

    def extract_vector(self, image_url: str) -> list[float]:
        if not image_url:
            raise ValueError("Thiếu đường dẫn ảnh để trích xuất.")

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(response.content)
            tmp.flush()
            path = tmp.name

        try:
            # enforce_detection=False để DeepFace không quăng lỗi crash
            reps = DeepFace.represent(img_path=path, model_name=self.model_name, 
                                     detector_backend=self.detector_backend, align=True,
                                     enforce_detection=False)
            
            if not reps:
                raise ValueError("Không tìm thấy khuôn mặt trong ảnh.")
                
            face_confidence = reps[0].get("face_confidence", 1.0)
            if face_confidence < self.detection_conf:
                raise ValueError(f"Ảnh quá mờ hoặc khuôn mặt không rõ (Độ tin cậy: {face_confidence:.2f} < {self.detection_conf}).")
                
            return [float(v) for v in reps[0]["embedding"]]
        except Exception as e:
            raise ValueError(f"Lỗi khi nhận diện khuôn mặt: {str(e)}")
        finally:
            os.remove(path)

    def search_qdrant(self, vector: list[float], student_id: str) -> dict[str, Any]:
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=qmodels.Filter(must=[qmodels.FieldCondition(
                key="student_id", match=qmodels.MatchValue(value=student_id))]),
            limit=1
        )

        if not results:
            return {"student_id": student_id, "score": 0.0, "matched": False, "reason": "Không tìm thấy dữ liệu khuôn mặt của sinh viên này trong hệ thống."}

        score = float(results[0].score or 0.0)
        similarity_threshold = self.match_threshold
        matched = score >= similarity_threshold
        
        if matched:
            reason = f"Nhận diện thành công (Độ tương đồng: {score:.4f} >= {similarity_threshold:.4f})."
        else:
            reason = f"Khuôn mặt không khớp với sinh viên '{student_id}' (Độ tương đồng: {score:.4f} < {similarity_threshold:.4f})."
            
        return {
            "student_id": student_id,
            "score": score,
            "matched": matched,
            "reason": reason,
            "threshold": similarity_threshold
        }