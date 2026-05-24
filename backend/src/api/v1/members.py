"""
Các API endpoint dùng cho việc đăng ký thành viên.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.user import (
    MemberRegistrationRequest,
    MemberRegistrationResponse,
    VideoMemberRegistrationRequest,
    VideoMemberRegistrationResponse,
)
from src.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/register", response_model=MemberRegistrationResponse)
def register_member(payload: MemberRegistrationRequest, db: Session = Depends(get_db)):
    """
    Đăng ký thành viên bằng ảnh mã hóa base64.

    - Yêu cầu ít nhất 3 ảnh (có thể cấu hình trong settings)
    - Trả về số chiều của embedding và số lượng ảnh được chấp nhận
    """
    result = MemberService.register_with_images(
        db=db,
        student_id=payload.student_id,
        name=payload.name,
        images_base64=payload.images_base64,
    )

    return MemberRegistrationResponse(
        student_id=result["student_id"],
        name=result["name"],
        embedding_dimension=result["embedding_dimension"],
        accepted_images=result["accepted_images"],
        stored_image_paths=result["stored_image_paths"],
        created_at=result["created_at"],
    )


@router.post("/register-video", response_model=VideoMemberRegistrationResponse)
async def register_member_video(
    student_id: str = Form(..., min_length=3, max_length=30),
    name: str = Form(..., min_length=1, max_length=255),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Đăng ký sinh viên bằng video quay mặt.

    - Video nên dài 10-20 giây với góc quay rõ mặt
    - Trích xuất 1 khung hình mỗi giây để lấy nhiều góc độ
    """
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên phải là video (mp4, webm, mov, ...).",
        )

    video_bytes = await video.read()

    result = MemberService.register_with_video(
        db=db,
        student_id=student_id,
        name=name,
        video_bytes=video_bytes,
    )

    return VideoMemberRegistrationResponse(
        student_id=result["student_id"],
        name=result["name"],
        embedding_dimension=result["embedding_dimension"],
        frames_processed=result["frames_processed"],
        created_at=result["created_at"],
    )


# Các endpoint backend cũ (giữ lại dưới dạng comment để tham khảo)
# @router.post("/register", response_model=MemberRegistrationResponse, status_code=status.HTTP_202_ACCEPTED)
# def register_member(payload: MemberRegistrationRequest, db: Session = Depends(get_db)):
#     """
#     1. Upsert user record in MySQL.
#     2. Upload each registration image to MinIO.
#     3. Send async Celery task to extract face embeddings and store in Qdrant + MySQL.
#     """
#     user = db.query(User).filter(User.student_id == payload.student_id).first()
#     if user is None:
#         user = User(student_id=payload.student_id, name=payload.name, class_name=payload.class_name)
#         db.add(user)
#     else:
#         user.name = payload.name
#         user.class_name = payload.class_name
#
#     db.commit()
#     db.refresh(user)
#
#     object_names: list[str] = []
#     for img_b64 in payload.images_base64:
#         obj_name = storage_service.save_image(img_b64, payload.student_id, prefix="register")
#         object_names.append(obj_name)
#
#     if not object_names:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Could not save images to storage.",
#         )
#
#     task = celery_app.send_task(
#         "register_face_task",
#         kwargs={
#             "student_id": payload.student_id,
#             "object_names": object_names,
#         },
#     )
#
#     return MemberRegistrationResponse(
#         student_id=user.student_id,
#         name=user.name,
#         status="processing",
#         task_id=task.id,
#         message="Da nhan thong tin dang ky. AI dang tien hanh trich xuat du lieu khuon mat.",
#     )
#
#
# @router.get("/{student_id}", response_model=MemberInfoResponse)
# def get_member(student_id: str, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.student_id == student_id).first()
#     if user is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
#     return user
