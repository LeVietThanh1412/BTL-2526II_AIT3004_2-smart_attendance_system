from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.src.core.celery_client import recognize_face_task
from src.schemas.attendance import AttendanceCheckResponse
from src.services.storages import minio_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in", response_model=AttendanceCheckResponse)
async def check_in(
    image: UploadFile = File(...),
    camera_id: str = Form(default="cam_01"),
):
    """Diem danh bang hinh anh chup tu camera.
    Check-in using image from camera.

    Steps:
    1. Validate image format
    2. Upload to MinIO storage
    3. Send to worker for face recognition
    4. Return check-in result"""

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tep tai len phai la anh (File must be an image)",
        )

    file_bytes = await image.read()
    minio_url = minio_service.upload_image(
        file_bytes=file_bytes,
        filename=image.filename or "capture.jpg",
    )

    async_result = recognize_face_task.delay(minio_url)

    try:
        worker_result = async_result.get(timeout=5)
    except CeleryTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Qua thoi gian cho nhan dang mat (Face recognition task timed out)",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Loi worker nhan dang (Face recognition worker failed)",
        ) from exc

    if isinstance(worker_result, dict):
        return AttendanceCheckResponse(
            status=str(worker_result.get("status", "success")),
            student_id=str(worker_result.get("student_id", "")),
            message=str(worker_result.get("message", f"Diem danh hoan tat tu {camera_id} (Check-in completed)")),
        )

    return AttendanceCheckResponse(
        status="success",
        student_id="",
        message=str(worker_result),
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
