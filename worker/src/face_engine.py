import cv2
import numpy as np

class FaceEngine:
    def __init__(self):
        try:
            import insightface
            # Buffalo_l is a very common and accurate model for InsightFace
            self.app = insightface.app.FaceAnalysis(name='buffalo_l')
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self.initialized = True
        except ImportError:
            self.initialized = False
            print("WARNING: insightface not installed. AI features will not work properly.")

    def get_embedding(self, image_path: str):
        if not self.initialized:
            return None
            
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        faces = self.app.get(img)
        if not faces:
            return None
            
        # Lấy khuôn mặt lớn nhất trong khung hình
        faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
        return faces[0].embedding.tolist()

face_engine = FaceEngine()
