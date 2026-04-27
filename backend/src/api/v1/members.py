import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.celery import celery_app
from src.database import get_db
from src.models.user import User
from src.schemas.user import MemberRegistrationRequest, MemberRegistrationResponse
from src.services.storages import storage_service

router = APIRouter(prefix="/members", tags=["members"])

@router.post("/register", response_model=MemberRegistrationResponse)
def register_member(payload: MemberRegistrationRequest, db: Session = Depends(get_db)):
	# 1. Lưu thông tin User (Text) vào DB MySQL đồng bộ
	user = db.query(User).filter(User.student_id == payload.student_id).first()
	if user is None:
		user = User(student_id=payload.student_id, name=payload.name, class_name=payload.class_name)
		db.add(user)
	else:
		user.name = payload.name
		user.class_name = payload.class_name
	
	db.commit()
	db.refresh(user)

	# 2. Lưu các file ảnh vào Storage (MinIO hoặc Local) đồng bộ
	stored_image_paths: list[str] = []
	for image_b64 in payload.images_base64:
		image_path = storage_service.save_image(image_b64, payload.student_id, prefix="register")
		stored_image_paths.append(image_path)

	if not stored_image_paths:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Could not save images.",
		)

	# 3. Gọi Worker qua Celery để trích xuất Vector Khuôn mặt (bất đồng bộ)
	task = celery_app.send_task(
		"register_face_task",
		kwargs={
			"student_id": payload.student_id,
			"image_paths": stored_image_paths
		}
	)

	# 4. Trả về ngay lập tức cho Frontend
	return MemberRegistrationResponse(
		student_id=user.student_id,
		name=user.name,
		status="processing",
		task_id=task.id,
		message="Đã nhận thông tin đăng ký. AI đang tiến hành trích xuất dữ liệu khuôn mặt."
	)
