import json
import uuid
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from src.celery_app import celery_app
from src.face_engine import face_engine
from src.database import SessionLocal, User, FaceEmbedding, AttendanceLog, AttendanceStatus
from src.config import settings

qdrant = QdrantClient(url=settings.QDRANT_URL)
COLLECTION_NAME = "faces"

# Đảm bảo Collection tồn tại trong Qdrant
try:
    qdrant.get_collection(COLLECTION_NAME)
except Exception:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qdrant_models.VectorParams(size=512, distance=qdrant_models.Distance.COSINE),
    )

@celery_app.task(name="register_face_task")
def register_face_task(student_id: str, image_paths: list):
    embeddings = []
    for path in image_paths:
        emb = face_engine.get_embedding(path)
        if emb is not None:
            embeddings.append(emb)
    
    if not embeddings:
        return {"status": "failed", "message": "No face detected in provided images"}
    
    # Tính trung bình các vector khuôn mặt để ra Master Vector (chính xác hơn)
    master_embedding = np.mean(embeddings, axis=0).tolist()
    
    # 1. Lưu Master Vector vào Qdrant (Vector DB)
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            qdrant_models.PointStruct(
                id=str(uuid.uuid4()),
                vector=master_embedding,
                payload={"student_id": student_id}
            )
        ]
    )
    
    # 2. Lưu liên kết ánh xạ vào MySQL
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.student_id == student_id).first()
        if user:
            existing = db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user.id).first()
            if existing:
                existing.embedding_vector = json.dumps(master_embedding)
                existing.image_paths = json.dumps(image_paths)
            else:
                db.add(FaceEmbedding(
                    user_id=user.id,
                    embedding_vector=json.dumps(master_embedding),
                    image_paths=json.dumps(image_paths)
                ))
            db.commit()
    finally:
        db.close()
        
    return {"status": "success", "student_id": student_id, "message": "Face registered successfully"}


@celery_app.task(name="process_attendance_frame_task")
def process_attendance_frame_task(image_path: str):
    # 1. Quét ảnh
    emb = face_engine.get_embedding(image_path)
    if emb is None:
        return {"status": "failed", "message": "No face detected"}
    
    # 2. Tìm kiếm KNN trên Qdrant
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=emb,
        limit=1
    )
    
    success = False
    similarity = 0.0
    student_id = None
    
    if results:
        top_match = results[0]
        similarity = top_match.score
        if similarity >= settings.FACE_SIMILARITY_THRESHOLD:
            success = True
            student_id = top_match.payload.get("student_id")
            
    # 3. Ghi log kết quả nhận diện vào MySQL
    db = SessionLocal()
    try:
        user = None
        if student_id:
            user = db.query(User).filter(User.student_id == student_id).first()
            
        if user:
            db.add(AttendanceLog(
                user_id=user.id,
                similarity_score=similarity,
                status=AttendanceStatus.success if success else AttendanceStatus.failed,
                minio_image_url=image_path
            ))
            db.commit()
    finally:
        db.close()
        
    return {
        "status": "success" if success else "failed",
        "student_id": student_id,
        "similarity": similarity
    }
