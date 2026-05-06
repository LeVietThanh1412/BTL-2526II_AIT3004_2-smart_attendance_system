from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.Base import Base

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    qdrant_id = Column(String(255), nullable=False, unique=True, index=True)
    image_path = Column(String(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="embedding")

    @property
    def minio_image_url(self) -> str:
        return self.image_path

    @minio_image_url.setter
    def minio_image_url(self, value: str) -> None:
        self.image_path = value

    @property
    def qdrant_vector_id(self) -> str:
        return self.qdrant_id

    @qdrant_vector_id.setter
    def qdrant_vector_id(self, value: str) -> None:
        self.qdrant_id = value

    @property
    def embedding_vector(self):
        return None

    @embedding_vector.setter
    def embedding_vector(self, value) -> None:
        _ = value

    @property
    def image_paths(self):
        return [self.image_path]

    @image_paths.setter
    def image_paths(self, value) -> None:
        _ = value