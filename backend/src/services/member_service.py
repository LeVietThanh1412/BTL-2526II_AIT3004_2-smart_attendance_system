import base64
import logging
from typing import List

import cv2
import numpy as np
from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.celery_client import extract_face_embedding_task
from src.core.config import settings
from src.core.qdrant_client import ensure_qdrant_collection, upsert_embedding
from src.models.face_embedding import FaceEmbedding
from src.models.user import User
from src.services.redis_query import redis_embedding_cache
from src.services.storages import minio_service
from src.utils.video_processor import extract_frames_from_video

logger = logging.getLogger(__name__)


class MemberService:
    """
    Dịch vụ xử lý logic nghiệp vụ cho việc đăng ký thành viên.

    Xu ly dang ky thanh vien bao gom:
    - Upload anh/video len MinIO
    - Trich xuat face embedding qua Celery task
    - Luu vector vao Qdrant
    - Cap nhat database User, FaceEmbedding
    - Luu cache Redis
    """

    @staticmethod
    def _process_images_batch(
        images_base64: List[str],
        student_id: str,
        prefix: str = "register",
    ) -> tuple[List[str], List[np.ndarray]]:
        """
        Xử lý hàng loạt ảnh base64: tải lên MinIO và trích xuất embedding.

        Xu ly loat anh base64: tai len MinIO va trich xuat embedding.

        Args:
            images_base64: Danh sách các ảnh đã mã hóa base64
            student_id: Mã sinh viên dùng để đặt tên file
            prefix: Tiền tố cho tên file khi tải lên

        Returns:
            Tuple gồm (danh sách đường dẫn ảnh đã lưu, danh sách các embedding)
        """
        embeddings: List[np.ndarray] = []
        stored_image_paths: List[str] = []

        for idx, image_b64 in enumerate(images_base64):
            try:
                image_data = base64.b64decode(
                    image_b64.split(",")[1] if "," in image_b64 else image_b64
                )
                filename = f"{prefix}_{student_id}_{idx}.jpg"

                image_path = minio_service.upload_image(file_bytes=image_data, filename=filename)
                stored_image_paths.append(image_path)

                try:
                    result = extract_face_embedding_task.delay(image_path).get(timeout=120)
                    if (
                        isinstance(result, dict)
                        and result.get("status") == "success"
                        and result.get("vector")
                    ):
                        embeddings.append(np.array(result["vector"], dtype=np.float32))
                    elif isinstance(result, dict) and result.get("status") == "failed":
                        logger.warning(
                            "Trích xuất embedding thất bại cho ảnh thứ %d của sinh viên %s: %s",
                            idx, student_id, result.get("message", "Lỗi không xác định"),
                        )
                except CeleryTimeoutError:
                    logger.warning(
                        "Quá thời gian xử lý Celery khi trích xuất embedding cho ảnh thứ %d của sinh viên %s",
                        idx, student_id,
                    )
                    continue
                except Exception as exc:
                    logger.error(
                        "Lỗi không mong muốn khi trích xuất embedding cho ảnh thứ %d của sinh viên %s: %s",
                        idx, student_id, exc, exc_info=True,
                    )
                    continue
            except Exception as exc:
                logger.error(
                    "Lỗi khi xử lý ảnh thứ %d của sinh viên %s: %s",
                    idx, student_id, exc, exc_info=True,
                )
                continue

        return stored_image_paths, embeddings

    @staticmethod
    def _process_video_batch(
        video_bytes: bytes,
        student_id: str,
    ) -> tuple[List[str], List[np.ndarray]]:
        """
        Xử lý video: trích xuất các khung hình, tải lên MinIO, trích xuất embedding.

        Xu ly video: trich xuat khung hinh, tai len MinIO, trich xuat embedding.

        Args:
            video_bytes: Dữ liệu file video thô
            student_id: Mã sinh viên dùng để đặt tên file

        Returns:
            Tuple gồm (danh sách đường dẫn ảnh đã lưu, danh sách các embedding)
        """
        try:
            frames = extract_frames_from_video(video_bytes, frame_interval=1)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi xử lý video: {exc}",
            ) from exc

        embeddings: List[np.ndarray] = []
        stored_image_paths: List[str] = []

        for idx, frame in enumerate(frames):
            try:
                _, buffer = cv2.imencode(".jpg", frame)
                image_data = buffer.tobytes()
                filename = f"register_video_{student_id}_{idx}.jpg"

                image_path = minio_service.upload_image(file_bytes=image_data, filename=filename)
                stored_image_paths.append(image_path)

                try:
                    result = extract_face_embedding_task.delay(image_path).get(timeout=120)
                    if (
                        isinstance(result, dict)
                        and result.get("status") == "success"
                        and result.get("vector")
                    ):
                        embeddings.append(np.array(result["vector"], dtype=np.float32))
                    elif isinstance(result, dict) and result.get("status") == "failed":
                        logger.warning(
                            "Trích xuất embedding thất bại cho khung hình %d của sinh viên %s: %s",
                            idx, student_id, result.get("message", "Lỗi không xác định"),
                        )
                except CeleryTimeoutError:
                    logger.warning(
                        "Quá thời gian xử lý Celery khi trích xuất embedding cho khung hình %d của sinh viên %s",
                        idx, student_id,
                    )
                    continue
                except Exception as exc:
                    logger.error(
                        "Lỗi không mong muốn khi trích xuất embedding cho khung hình %d của sinh viên %s: %s",
                        idx, student_id, exc, exc_info=True,
                    )
                    continue
            except Exception as exc:
                logger.error(
                    "Lỗi khi xử lý khung hình %d của sinh viên %s: %s",
                    idx, student_id, exc, exc_info=True,
                )
                continue

        return stored_image_paths, embeddings

    @staticmethod
    def _save_user_and_embedding(
        db: Session,
        student_id: str,
        name: str,
        master_embedding_list: List[float],
        stored_image_paths: List[str],
    ) -> User:
        """
        Lưu hoặc cập nhật thông tin người dùng và face embedding vào database.

        Luu hoac cap nhat nguoi dung va face embedding trong database.

        Args:
            db: Session của database
            student_id: Mã sinh viên
            name: Tên sinh viên
            master_embedding_list: Vector embedding tham chiếu
            stored_image_paths: Danh sách các đường dẫn ảnh đã tải lên MinIO

        Returns:
            Đối tượng User
        """
        user = db.query(User).filter(User.student_id == student_id).first()
        if user is None:
            user = User(student_id=student_id, name=name)
            db.add(user)
            db.flush()
        else:
            if user.is_approved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Sinh viên '{student_id}' đã được đăng ký và duyệt. Không thể đăng ký lại.",
                )
            user.name = name

        qdrant_point_id = user.id

        try:
            upsert_embedding(
                user_id=qdrant_point_id,
                student_id=student_id,
                vector=master_embedding_list,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Không thể lưu vector khuôn mặt vào Qdrant: {exc}",
            ) from exc

        if user.embedding is None:
            embedding_row = FaceEmbedding(
                user_id=user.id,
                minio_image_url=stored_image_paths[0],
                qdrant_vector_id=str(qdrant_point_id),
            )
            db.add(embedding_row)
        else:
            user.embedding.minio_image_url = stored_image_paths[0]
            user.embedding.qdrant_vector_id = str(qdrant_point_id)

        db.commit()
        db.refresh(user)

        return user

    @classmethod
    def register_with_images(
        cls,
        db: Session,
        student_id: str,
        name: str,
        images_base64: List[str],
    ) -> dict:
        """
        Đăng ký thành viên bằng ảnh mã hóa base64.

        Dang ky thanh vien bang anh ma hoa base64.

        Args:
            db: Session của database
            student_id: Mã sinh viên
            name: Tên sinh viên
            images_base64: Danh sách ảnh đã mã hóa base64

        Returns:
            Dictionary chứa kết quả đăng ký
        """
        if len(images_base64) < settings.min_registration_images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cần ít nhất {settings.min_registration_images} ảnh để đăng ký.",
            )

        stored_image_paths, embeddings = cls._process_images_batch(
            images_base64=images_base64,
            student_id=student_id,
        )

        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không trích xuất được embedding khuôn mặt từ các ảnh đăng ký. Kiểm tra lại ảnh chụp.",
            )

        master_embedding = np.mean(np.stack(embeddings), axis=0)
        master_embedding_list = master_embedding.astype(float).tolist()

        ensure_qdrant_collection(vector_size=len(master_embedding_list))

        user = cls._save_user_and_embedding(
            db=db,
            student_id=student_id,
            name=name,
            master_embedding_list=master_embedding_list,
            stored_image_paths=stored_image_paths,
        )

        redis_embedding_cache.set_embedding(student_id, master_embedding_list)

        return {
            "student_id": user.student_id,
            "name": user.name,
            "embedding_dimension": len(master_embedding_list),
            "accepted_images": len(embeddings),
            "stored_image_paths": stored_image_paths,
            "created_at": user.created_at,
        }

    @classmethod
    def register_with_video(
        cls,
        db: Session,
        student_id: str,
        name: str,
        video_bytes: bytes,
    ) -> dict:
        """
        Đăng ký thành viên bằng video quay mặt.

        Dang ky thanh vien bang video quay mat.

        Args:
            db: Session của database
            student_id: Mã sinh viên
            name: Tên sinh viên
            video_bytes: Dữ liệu file video thô

        Returns:
            Dictionary chứa kết quả đăng ký
        """
        stored_image_paths, embeddings = cls._process_video_batch(
            video_bytes=video_bytes,
            student_id=student_id,
        )

        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không trích xuất được embedding khuôn mặt từ video. Đảm bảo khuôn mặt hiện rõ trong video.",
            )

        master_embedding = np.mean(np.stack(embeddings), axis=0)
        master_embedding_list = master_embedding.astype(float).tolist()

        ensure_qdrant_collection(vector_size=len(master_embedding_list))

        user = cls._save_user_and_embedding(
            db=db,
            student_id=student_id,
            name=name,
            master_embedding_list=master_embedding_list,
            stored_image_paths=stored_image_paths,
        )

        redis_embedding_cache.set_embedding(student_id, master_embedding_list)

        return {
            "student_id": user.student_id,
            "name": user.name,
            "embedding_dimension": len(master_embedding_list),
            "frames_processed": len(embeddings),
            "created_at": user.created_at,
        }
