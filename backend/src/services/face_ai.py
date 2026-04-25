import base64
import binascii
from io import BytesIO

import cv2
import numpy as np
from fastapi import HTTPException, status
from PIL import Image

from src.core.config import settings


class FaceAIService:
    def __init__(self) -> None:
        self._yolo_model = None
        self._face_analysis = None

    def _load_yolo(self):
        if self._yolo_model is None:
            try:
                from ultralytics import YOLO
            except Exception as exc:
                raise RuntimeError(
                    "YOLO is not available. Install ultralytics and provide YOLO_MODEL_PATH."
                ) from exc
            self._yolo_model = YOLO(settings.yolo_model_path)
        return self._yolo_model

    def _load_face_analysis(self):
        if self._face_analysis is None:
            try:
                from insightface.app import FaceAnalysis
            except Exception as exc:
                raise RuntimeError(
                    "InsightFace is not available. Install insightface and onnxruntime."
                ) from exc

            self._face_analysis = FaceAnalysis(
                providers=["CPUExecutionProvider"],
            )
            self._face_analysis.prepare(ctx_id=-1, det_size=(640, 640))
        return self._face_analysis

    @staticmethod
    def _decode_base64_image(image_b64: str) -> np.ndarray:
        payload = image_b64.split(",", 1)[1] if "," in image_b64 else image_b64
        try:
            binary = base64.b64decode(payload)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image payload.",
            ) from exc

        try:
            pil_image = Image.open(BytesIO(binary)).convert("RGB")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot decode image content.",
            ) from exc

        rgb = np.array(pil_image)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _largest_box(boxes: np.ndarray) -> np.ndarray:
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        return boxes[int(np.argmax(areas))]

    def detect_and_crop_face(self, image_bgr: np.ndarray) -> np.ndarray:
        model = self._load_yolo()
        result = model.predict(image_bgr, verbose=False, conf=0.25)[0]
        boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else np.array([])
        if boxes.size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No face detected. Please provide a clearer face image.",
            )

        x1, y1, x2, y2 = self._largest_box(boxes).astype(int)
        h, w = image_bgr.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Detected face crop is invalid.",
            )
        return image_bgr[y1:y2, x1:x2]

    def extract_embedding(self, face_bgr: np.ndarray) -> np.ndarray:
        face_app = self._load_face_analysis()
        faces = face_app.get(face_bgr)
        if not faces:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot extract facial embedding from the captured image.",
            )
        return faces[0].embedding.astype(np.float32)

    def embedding_from_base64(self, image_b64: str) -> np.ndarray:
        image = self._decode_base64_image(image_b64)
        crop = self.detect_and_crop_face(image)
        return self.extract_embedding(crop)


face_ai_service = FaceAIService()
