"""
Quản lý kết nối Qdrant và các collection chứa vector.
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.core.config import settings


# Khởi tạo Qdrant client
qdrant_client = QdrantClient(url=settings.qdrant_url)


def ensure_qdrant_collection(vector_size: int) -> None:
    collection_name = settings.qdrant_collection
    
    collections = qdrant_client.get_collections().collections
    target_col = next((col for col in collections if col.name == collection_name), None)
    if target_col:
        info = qdrant_client.get_collection(collection_name)
        if info.config.params.vectors.size != vector_size:
            qdrant_client.delete_collection(collection_name)
        else:
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
    Thêm hoặc cập nhật face embedding vector vào collection trên Qdrant.

    Args:
        user_id: ID người dùng dùng làm point ID
        student_id: Mã sinh viên dùng để lưu vào payload
        vector: Face embedding vector (danh sách các số thực)

    Raises:
        Exception: Nếu thêm/cập nhật thất bại
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
    Kiểm tra xem sinh viên có vector khuôn mặt nào trong Qdrant không.

    Args:
        student_id: Mã sinh viên cần kiểm tra

    Returns:
        True nếu có ít nhất một vector của sinh viên
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
