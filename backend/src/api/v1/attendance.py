import logging

from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core.celery_client import recognize_face_task
from src.core.config import settings
from src.core.qdrant_client import has_vectors_for_student
from src.database import get_db
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User
from src.schemas.attendance import AttendanceCheckResponse
from src.services.storages import minio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in", response_model=AttendanceCheckResponse)
async def check_in(
    image: UploadFile = File(...),
    student_id: str = Form(..., min_length=3, max_length=30),
    camera_id: str = Form(default=settings.default_camera_id),
    db: Session = Depends(get_db),
):
    """Diem danh bang hinh anh chup tu camera kem ma sinh vien.
    Check-in using image from camera with student ID.

    Steps:
    1. Validate student_id exists in database
    2. Validate student has face vectors in Qdrant
    3. Validate image format
    4. Upload to MinIO storage
    5. Send to worker for face recognition (filtered by student_id)
    6. Return check-in result with match_score, threshold, matched, reason"""

    # --- Step 1: Validate student_id exists in database ---
    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        logger.warning("Check-in failed: student_id=%s not found in database", student_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã sinh viên '{student_id}' không tồn tại trong hệ thống.",
        )

    # --- Step 2: Validate student has vectors in Qdrant ---
    if not has_vectors_for_student(student_id):
        logger.warning("Check-in failed: student_id=%s has no face vectors", student_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sinh viên '{student_id}' chưa đăng ký khuôn mặt. Vui lòng đăng ký trước.",
        )

    # --- Step 3: Validate image format ---
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên phải là hình ảnh (jpg, png, webp, ...).",
        )

    # --- Step 4: Upload to MinIO ---
    file_bytes = await image.read()
    minio_url = minio_service.upload_image(
        file_bytes=file_bytes,
        filename=image.filename or "capture.jpg",
    )

    # --- Step 5: Send to worker with student_id ---
    async_result = recognize_face_task.delay(minio_url, student_id)

    try:
        worker_result = async_result.get(timeout=15)
    except CeleryTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Hết thời gian chờ nhận dạng khuôn mặt. Worker AI chưa phản hồi.",
        ) from exc
    except Exception as exc:
        logger.error("Worker error for student_id=%s: %s", student_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Worker nhận dạng khuôn mặt gặp lỗi. Vui lòng thử lại.",
        ) from exc

    # --- Step 6: Process worker result ---
    if not isinstance(worker_result, dict):
        worker_result = {
            "status": "failed",
            "student_id": student_id,
            "score": 0.0,
            "threshold": settings.face_similarity_threshold,
            "matched": False,
            "reason": str(worker_result),
            "message": str(worker_result),
        }

    status_value = str(worker_result.get("status", "failed")).lower()
    score = float(worker_result.get("score") or 0.0)
    threshold = float(worker_result.get("threshold") or settings.face_similarity_threshold)
    matched = bool(worker_result.get("matched", False))
    reason = worker_result.get("reason", "")
    message = worker_result.get("message", f"Điểm danh hoàn tất từ camera {camera_id}.")

    # Determine attendance status
    if matched and status_value == "success":
        status_enum = AttendanceStatus.success
    elif status_value == "quality_error":
        status_enum = AttendanceStatus.failed
    else:
        status_enum = AttendanceStatus.failed

    # Log result for debugging
    logger.info(
        "Check-in result: student_id=%s, match_score=%.4f, threshold=%.4f, matched=%s, reason=%s",
        student_id, score, threshold, matched, reason,
    )

    # --- Save attendance record ---
    attendance = Attendance(
        user_id=user.id,
        confidence_score=score,
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
        match_score=score,
        threshold=threshold,
        matched=matched,
        reason=reason,
        message=str(message),
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
