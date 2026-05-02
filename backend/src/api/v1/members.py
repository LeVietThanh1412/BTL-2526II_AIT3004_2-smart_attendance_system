from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.celery import celery_app
from src.database import get_db
from src.models.user import User
from src.schemas.user import MemberInfoResponse, MemberRegistrationRequest, MemberRegistrationResponse
from src.services.storages import storage_service

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/register", response_model=MemberRegistrationResponse, status_code=status.HTTP_202_ACCEPTED)
def register_member(payload: MemberRegistrationRequest, db: Session = Depends(get_db)):
    """
    1. Upsert user record in MySQL.
    2. Upload each registration image to MinIO.
    3. Send async Celery task to extract face embeddings and store in Qdrant + MySQL.
    """
    # 1. Upsert User
    user = db.query(User).filter(User.student_id == payload.student_id).first()
    if user is None:
        user = User(student_id=payload.student_id, name=payload.name, class_name=payload.class_name)
        db.add(user)
    else:
        user.name = payload.name
        user.class_name = payload.class_name

    db.commit()
    db.refresh(user)

    # 2. Upload images to MinIO (returns object_names, not local paths)
    object_names: list[str] = []
    for img_b64 in payload.images_base64:
        obj_name = storage_service.save_image(img_b64, payload.student_id, prefix="register")
        object_names.append(obj_name)

    if not object_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save images to storage.",
        )

    # 3. Dispatch async Celery task
    task = celery_app.send_task(
        "register_face_task",
        kwargs={
            "student_id": payload.student_id,
            "object_names": object_names,   # MinIO object names, not local paths
        },
    )

    return MemberRegistrationResponse(
        student_id=user.student_id,
        name=user.name,
        status="processing",
        task_id=task.id,
        message="Đã nhận thông tin đăng ký. AI đang tiến hành trích xuất dữ liệu khuôn mặt.",
    )


@router.get("/{student_id}", response_model=MemberInfoResponse)
def get_member(student_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return user
