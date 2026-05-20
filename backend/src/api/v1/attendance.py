from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core.celery_client import recognize_face_task
from src.core.config import settings
from src.database import get_db
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User
from src.schemas.attendance import AttendanceCheckResponse
from src.services.storages import minio_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in", response_model=AttendanceCheckResponse)
async def check_in(
    image: UploadFile = File(...),
    student_id: str = Form(...),
    camera_id: str = Form(default=settings.default_camera_id),
    db: Session = Depends(get_db),
):
    """Diem danh bang hinh anh chup tu camera.
    Check-in using image from camera.

    Steps:
    1. Validate image format
    2. Upload to MinIO storage
    3. Send to worker for face recognition
    4. Return check-in result"""

    student_id = str(student_id or "").strip()
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu mã sinh viên. Vui lòng nhập mã sinh viên trước khi điểm danh.",
        )

    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy mã sinh viên trong hệ thống.",
        )

    if user.embedding is None or not user.embedding.qdrant_vector_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinh viên chưa có vector khuôn mặt để đối chiếu.",
        )

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên phải là hình ảnh (jpg, png, webp, ...).",
        )

    file_bytes = await image.read()
    minio_url = minio_service.upload_image(
        file_bytes=file_bytes,
        filename=image.filename or "capture.jpg",
    )

    async_result = recognize_face_task.delay(minio_url, student_id)

    try:
        worker_result = async_result.get(timeout=5)
    except CeleryTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Hết thời gian chờ nhận dạng khuôn mặt. Worker AI chưa phản hồi.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Worker nhận dạng khuôn mặt gặp lỗi. Vui lòng thử lại.",
        ) from exc

    if not isinstance(worker_result, dict):
        worker_result = {
            "status": "failed",
            "student_id": student_id,
            "match_score": 0.0,
            "threshold": float(settings.face_similarity_threshold),
            "matched": False,
            "reason": str(worker_result),
        }

    status_value = str(worker_result.get("status", "failed")).lower()
    match_score = float(worker_result.get("match_score") or worker_result.get("score") or 0.0)
    threshold = float(worker_result.get("threshold") or settings.face_similarity_threshold)
    matched = bool(worker_result.get("matched"))
    if "matched" not in worker_result:
        matched = status_value == "success"
    reason = str(worker_result.get("reason") or worker_result.get("message") or "")

    status_enum = AttendanceStatus.success if matched else AttendanceStatus.failed

    status_value = "success" if matched else "failed"

    attendance = Attendance(
        user_id=user.id if user else None,
        confidence_score=match_score,
        camera_id=camera_id,
        status=status_enum,
    )

    try:
        db.add(attendance)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu log điểm danh. Vui lòng thử lại.",
        ) from exc

    return AttendanceCheckResponse(
        status=status_value,
        student_id=student_id,
        match_score=match_score,
        threshold=threshold,
        matched=matched,
        reason=reason or f"Điểm danh hoàn tất từ camera {camera_id}.",
        message=str(worker_result.get("message", "")) or None,
    )


# Legacy backend attendance endpoints (commented to preserve differences)
# @router.post("/verify", response_model=AttendanceVerifyResponse, status_code=status.HTTP_202_ACCEPTED)
# def verify_attendance(payload: AttendanceVerifyRequest):
#     """
#     1. Upload attendance frame to MinIO.
#     2. Dispatch async Celery task for face recognition.
#     3. Return task_id immediately for frontend to poll.
#     """
#     object_name = storage_service.save_image(
#         payload.image_base64,
#         "attendance_frames",
#         prefix="frame",
#     )
#
#     task = celery_app.send_task(
#         "process_attendance_frame_task",
#         kwargs={"object_name": object_name},
#     )
#
#     return AttendanceVerifyResponse(
#         status="processing",
#         task_id=task.id,
#         message="Da nhan frame anh. AI Worker dang xu ly nhan dien.",
#     )
#
#
# @router.get("/result/{task_id}", response_model=AttendanceResultResponse)
# def get_attendance_result(task_id: str):
#     """
#     Poll for attendance recognition result.
#     The worker stores results in Redis; this endpoint reads from there.
#     """
#     cached = attendance_result_cache.get_result(task_id)
#     if cached is not None:
#         return AttendanceResultResponse(task_id=task_id, **cached)
#
#     task = celery_app.AsyncResult(task_id)
#     if task.state == "PENDING":
#         return AttendanceResultResponse(task_id=task_id, status="processing", message="Dang xu ly...")
#     if task.state == "SUCCESS" and isinstance(task.result, dict):
#         return AttendanceResultResponse(task_id=task_id, **task.result)
#     if task.state == "FAILURE":
#         return AttendanceResultResponse(task_id=task_id, status="failed", message=str(task.result))
#
#     return AttendanceResultResponse(task_id=task_id, status="processing", message="Dang xu ly...")
