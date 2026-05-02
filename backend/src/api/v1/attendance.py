from fastapi import APIRouter

from src.core.celery import celery_app
from src.schemas.attendance import AttendanceVerifyRequest, AttendanceVerifyResponse
from src.services.storages import storage_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.post("/verify", response_model=AttendanceVerifyResponse)
def verify_attendance(payload: AttendanceVerifyRequest):
	# 1. Lưu frame ảnh từ Frontend
	captured_path = storage_service.save_image(
		payload.image_base64,
		"unknown_student",
		prefix="attendance",
	)

	# 2. Gửi Task quét mặt cho Celery Worker
	task = celery_app.send_task(
		"process_attendance_frame_task",
		kwargs={"image_path": captured_path}
	)

	# 3. Phản hồi HTTP ngay lập tức
	return AttendanceVerifyResponse(
		status="processing",
		task_id=task.id,
		message="Đã nhận frame ảnh. AI Worker đang xử lý nhận diện."
	)
