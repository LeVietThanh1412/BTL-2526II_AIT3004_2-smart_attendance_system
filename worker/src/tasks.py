import json
import uuid
from datetime import datetime

import numpy as np
from minio import Minio
from minio.error import S3Error
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from redis import Redis

from src.celery_app import celery_app
from src.config import settings
from src.database import AttendanceLog, AttendanceStatus, FaceEmbedding, SessionLocal, User
from src.face_engine import EMBEDDING_SIZE, face_engine

# ---------------------------------------------------------------------------
# Shared clients (module-level singletons; each worker process has its own)
# ---------------------------------------------------------------------------

_qdrant = QdrantClient(url=settings.qdrant_url)
_redis = Redis.from_url(settings.redis_url, decode_responses=True)
_minio = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

COLLECTION_NAME = "faces"
_RESULT_PREFIX = "attendance:result:"


def _ensure_qdrant_collection() -> None:
    try:
        _qdrant.get_collection(COLLECTION_NAME)
    except Exception:
        _qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(
                size=EMBEDDING_SIZE,
                distance=qdrant_models.Distance.COSINE,
            ),
        )


_ensure_qdrant_collection()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download_from_minio(object_name: str) -> bytes:
    """Download an object from MinIO and return raw bytes."""
    response = _minio.get_object(settings.minio_bucket_name, object_name)
    return response.read()


def _cache_result(task_id: str, data: dict, ttl: int = 300) -> None:
    try:
        _redis.setex(f"{_RESULT_PREFIX}{task_id}", ttl, json.dumps(data, default=str))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="register_face_task", bind=True, max_retries=3)
def register_face_task(self, student_id: str, object_names: list[str]):
    """
    1. Download each registration image from MinIO.
    2. Extract face embeddings using DeepFace.
    3. Average embeddings → master embedding.
    4. Upsert into Qdrant (delete old point first to maintain 1-point-per-student).
    5. Update FaceEmbedding record in MySQL.
    """
    embeddings = []
    for obj_name in object_names:
        try:
            img_bytes = _download_from_minio(obj_name)
        except Exception as e:
            print(f"[register_face_task] Cannot download {obj_name}: {e}")
            continue

        emb = face_engine.get_embedding_from_bytes(img_bytes)
        if emb is not None:
            embeddings.append(emb)

    if not embeddings:
        return {"status": "failed", "student_id": student_id, "message": "No face detected in provided images"}

    # Average → master vector (already L2-normalised per image, renormalise after mean)
    master_arr = np.mean(embeddings, axis=0).astype(np.float32)
    norm = np.linalg.norm(master_arr)
    if norm > 0:
        master_arr /= norm
    master_embedding = master_arr.tolist()

    # Qdrant: delete any existing point for this student, then upsert new one
    _qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=qdrant_models.FilterSelector(
            filter=qdrant_models.Filter(
                must=[qdrant_models.FieldCondition(
                    key="student_id",
                    match=qdrant_models.MatchValue(value=student_id),
                )]
            )
        ),
    )
    point_id = str(uuid.uuid4())
    _qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            qdrant_models.PointStruct(
                id=point_id,
                vector=master_embedding,
                payload={"student_id": student_id},
            )
        ],
    )

    # MySQL: upsert FaceEmbedding
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.student_id == student_id).first()
        if user:
            existing = db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user.id).first()
            if existing:
                existing.embedding_vector = json.dumps(master_embedding)
                existing.image_paths = json.dumps(object_names)
            else:
                db.add(FaceEmbedding(
                    user_id=user.id,
                    embedding_vector=json.dumps(master_embedding),
                    image_paths=json.dumps(object_names),
                ))
            db.commit()
    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=5)
    finally:
        db.close()

    return {"status": "success", "student_id": student_id, "message": "Face registered successfully"}


@celery_app.task(name="process_attendance_frame_task", bind=True, max_retries=2)
def process_attendance_frame_task(self, object_name: str):
    """
    1. Download attendance frame from MinIO.
    2. Extract face embedding.
    3. Search Qdrant for nearest neighbour.
    4. Log result to MySQL.
    5. Cache result in Redis so backend /result endpoint can serve it instantly.
    """
    task_id = self.request.id

    # 1. Download frame
    try:
        img_bytes = _download_from_minio(object_name)
    except Exception as e:
        result = {"status": "failed", "message": f"Cannot download frame: {e}"}
        _cache_result(task_id, result)
        return result

    # 2. Extract embedding
    emb = face_engine.get_embedding_from_bytes(img_bytes)
    if emb is None:
        result = {"status": "failed", "message": "No face detected in frame"}
        _cache_result(task_id, result)
        return result

    # 3. KNN search in Qdrant
    hits = _qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=emb,
        limit=1,
        score_threshold=settings.face_similarity_threshold,
    )

    recognized = bool(hits)
    similarity = round(hits[0].score, 4) if hits else 0.0
    student_id = hits[0].payload.get("student_id") if hits else None

    # 4. Log to MySQL
    db = SessionLocal()
    user_name = None
    try:
        user = None
        if student_id:
            user = db.query(User).filter(User.student_id == student_id).first()

        log_status = AttendanceStatus.success if (recognized and user) else AttendanceStatus.failed
        log = AttendanceLog(
            similarity_score=similarity,
            status=log_status,
            minio_image_url=object_name,
        )
        if user:
            log.user_id = user.id
            user_name = user.name
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[process_attendance_frame_task] DB error: {e}")
    finally:
        db.close()

    result = {
        "status": "success" if recognized else "failed",
        "student_id": student_id,
        "name": user_name,
        "similarity": similarity,
        "message": "Nhận diện thành công." if recognized else "Không nhận diện được khuôn mặt.",
        "timestamp": datetime.utcnow().isoformat(),
    }
    _cache_result(task_id, result)
    return result
