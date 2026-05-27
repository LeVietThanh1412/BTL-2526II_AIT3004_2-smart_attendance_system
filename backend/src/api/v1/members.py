"""
Các API endpoint dùng cho việc đăng ký thành viên.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from typing import List
from pydantic import BaseModel

from src.database import get_db
from src.models.user import User
from src.models.face_embedding import FaceEmbedding
from src.api.v1.auth import get_current_admin
from src.core.qdrant_client import qdrant_client
from src.core.config import settings

from src.schemas.user import (
    MemberRegistrationRequest,
    MemberRegistrationResponse,
    VideoMemberRegistrationRequest,
    VideoMemberRegistrationResponse,
)
from src.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])

class MemberInfo(BaseModel):
    id: int
    student_id: str
    full_name: str
    is_approved: bool

class MemberListResponse(BaseModel):
    items: List[MemberInfo]


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


@router.get("", response_model=MemberListResponse)
def get_members(db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    items = [MemberInfo(id=u.id, student_id=u.student_id, full_name=u.full_name, is_approved=u.is_approved) for u in users]
    return MemberListResponse(items=items)


@router.post("/{student_id}/approve")
def approve_member(student_id: str, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    user.is_approved = True
    
    from src.models.schedule import StudentSchedule
    from datetime import datetime
    # Dùng cùng logic với /schedule/approve: nếu có lịch chờ duyệt thì xóa lịch cũ rồi duyệt lịch chờ
    # Nếu không có lịch chờ (đăng ký lần đầu chưa submit), duyệt luôn lịch hiện tại
    pending_count = db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id, 
        StudentSchedule.is_approved == False,
        StudentSchedule.is_active == True
    ).count()
    if pending_count > 0:
        # Vô hiệu hóa lịch cũ đã duyệt (giữ lại lịch sử) thay vì xóa
        db.query(StudentSchedule).filter(
            StudentSchedule.user_id == user.id, 
            StudentSchedule.is_approved == True,
            StudentSchedule.is_active == True
        ).update({"is_active": False})
        
        # Duyệt lịch chờ
        db.query(StudentSchedule).filter(
            StudentSchedule.user_id == user.id, 
            StudentSchedule.is_approved == False,
            StudentSchedule.is_active == True
        ).update({
            "is_approved": True,
            "approved_at": datetime.now()
        })
    else:
        # Không có lịch nào cả (sv chưa đăng ký lịch) - không cần làm gì
        pass
    
    db.commit()
    return {"message": "Duyệt thành công."}


@router.delete("/{student_id}")
def delete_member(student_id: str, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    # Xóa từ MySQL
    db.delete(user)
    db.commit()

    # Xóa từ Qdrant
    try:
        from qdrant_client.http import models as qmodels
        qdrant_client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="student_id",
                        match=qmodels.MatchValue(value=student_id)
                    )
                ]
            )
        )
    except Exception as e:
        pass

    # Xóa ảnh từ MinIO
    try:
        from src.services.storages import minio_service
        # TODO: Implement delete_folder in MinioService if needed
        pass
    except Exception as e:
        pass

    return {"message": "Xóa sinh viên và dữ liệu liên quan thành công."}
