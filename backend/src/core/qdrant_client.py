"""
Qdrant vector database client and collection management.
Quan ly ket noi Qdrant va cac collection vector.
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.core.config import settings


# Initialize Qdrant client
qdrant_client = QdrantClient(url=settings.qdrant_url)


def ensure_qdrant_collection(vector_size: int) -> None:
    """
    Ensure Qdrant collection exists for face embeddings.
    If collection doesn't exist, create it with specified vector size.

    Dam bao collection Qdrant ton tai cho face embeddings.
    Neu collection khong ton tai, tao no voi kich thuoc vector cu the.

    Args:
        vector_size: Dimension of face embedding vectors (typically 512 for ArcFace, 128 for FaceNet)
    """
    collection_name = settings.qdrant_collection
    collections = qdrant_client.get_collections().collections
    if any(col.name == collection_name for col in collections):
        return
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
    )


def upsert_embedding(
    user_id: int,
    student_id: str,
    vector: list,
) -> None:
    """
    Upsert face embedding vector to Qdrant collection.

    Them hoac cap nhat face embedding vector vao collection Qdrant.

    Args:
        user_id: User ID to use as point ID
        student_id: Student ID for payload
        vector: Face embedding vector (list of floats)

    Raises:
        Exception: If upsert fails
    """
    qdrant_client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qmodels.PointStruct(
                id=user_id,
                vector=vector,
                payload={
                    "student_id": student_id,
                    "user_id": user_id,
                },
            )
        ],
    )


def has_vectors_for_student(student_id: str) -> bool:
    """
    Check if a student has any face embedding vectors in Qdrant.

    Kiem tra xem sinh vien co vector khuon mat nao trong Qdrant khong.

    Args:
        student_id: Student ID to check

    Returns:
        True if at least one vector exists for the student
    """
    try:
        results, _ = qdrant_client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="student_id",
                        match=qmodels.MatchValue(value=student_id),
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        return len(results) > 0
    except Exception:
        return False
