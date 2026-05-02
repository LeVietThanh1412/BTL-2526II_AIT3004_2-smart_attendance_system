from fastapi import APIRouter, status

from src.core.celery import celery_app
from src.schemas.attendance import AttendanceResultResponse, AttendanceVerifyRequest, AttendanceVerifyResponse
from src.services.face_ai import attendance_result_cache
from src.services.storages import storage_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/verify", response_model=AttendanceVerifyResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_attendance(payload: AttendanceVerifyRequest):
    """
    1. Upload attendance frame to MinIO.
    2. Dispatch async Celery task for face recognition.
    3. Return task_id immediately for frontend to poll.
    """
    # Upload raw frame to MinIO
    object_name = storage_service.save_image(
        payload.image_base64,
        "attendance_frames",
        prefix="frame",
    )

    # Dispatch worker task with MinIO object name
    task = celery_app.send_task(
        "process_attendance_frame_task",
        kwargs={"object_name": object_name},
    )

    return AttendanceVerifyResponse(
        status="processing",
        task_id=task.id,
        message="Đã nhận frame ảnh. AI Worker đang xử lý nhận diện.",
    )


@router.get("/result/{task_id}", response_model=AttendanceResultResponse)
def get_attendance_result(task_id: str):
    """
    Poll for attendance recognition result.
    The worker stores results in Redis; this endpoint reads from there.
    """
    cached = attendance_result_cache.get_result(task_id)
    if cached is not None:
        return AttendanceResultResponse(task_id=task_id, **cached)

    # Fallback: check Celery task state
    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return AttendanceResultResponse(task_id=task_id, status="processing", message="Đang xử lý...")
    if task.state == "SUCCESS" and isinstance(task.result, dict):
        return AttendanceResultResponse(task_id=task_id, **task.result)
    if task.state == "FAILURE":
        return AttendanceResultResponse(task_id=task_id, status="failed", message=str(task.result))

    return AttendanceResultResponse(task_id=task_id, status="processing", message="Đang xử lý...")
