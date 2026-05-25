from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from src.database import get_db
from src.models.user import User
from src.models.schedule import StudentSchedule
from src.schemas.schedule import ScheduleListUpdate, ScheduleResponse, ScheduleHistoryResponse
from src.api.v1.auth import get_current_admin

router = APIRouter(prefix="/schedule", tags=["schedule"])

# IMPORTANT: /history must come BEFORE /{student_id} to avoid being captured as student_id="history"
@router.get("/{student_id}/history")
def get_schedule_history(student_id: str, db: Session = Depends(get_db)):
    """Lấy lịch sử đổi ca học của sinh viên"""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    all_schedules = db.query(StudentSchedule).filter(StudentSchedule.user_id == user.id).all()
    
    # Nhóm theo created_at (round về giây để tránh microsecond diff)
    history_groups = {}
    for s in all_schedules:
        created_key = s.created_at.replace(microsecond=0) if s.created_at else None
        key = (created_key, s.is_approved)
        if key not in history_groups:
            history_groups[key] = {"schedules": [], "approved_at": s.approved_at}
        history_groups[key]["schedules"].append({
            "day_of_week": s.day_of_week,
            "shifts": s.shifts
        })
        if s.approved_at and not history_groups[key]["approved_at"]:
            history_groups[key]["approved_at"] = s.approved_at
    
    result = []
    for (created_at, is_approved), group in history_groups.items():
        result.append({
            "created_at": created_at.isoformat() if created_at else None,
            "approved_at": group["approved_at"].isoformat() if group["approved_at"] else None,
            "is_approved": is_approved,
            "schedules": sorted(group["schedules"], key=lambda x: x["day_of_week"])
        })
    
    result.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return result


@router.get("/{student_id}", response_model=List[ScheduleResponse])
def get_student_schedule(student_id: str, db: Session = Depends(get_db)):
    """Lấy danh sách lịch học đang active (approved + pending) của sinh viên"""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    return db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id,
        StudentSchedule.is_active == True
    ).order_by(StudentSchedule.is_approved.desc(), StudentSchedule.day_of_week).all()


@router.post("/{student_id}")
def update_student_schedule(
    student_id: str, 
    payload: ScheduleListUpdate, 
    db: Session = Depends(get_db)
):
    """Cập nhật toàn bộ lịch học của sinh viên (gửi yêu cầu đổi ca)."""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    # Disable các yêu cầu đổi lịch đang chờ duyệt (giữ lại lịch sử)
    db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id, 
        StudentSchedule.is_approved == False,
        StudentSchedule.is_active == True
    ).update({"is_active": False})
    
    now = datetime.now()
    new_schedules = []
    for schedule_data in payload.schedules:
        new_schedule = StudentSchedule(
            user_id=user.id,
            day_of_week=schedule_data.day_of_week,
            shifts=schedule_data.shifts,
            is_approved=False,
            is_active=True,
            created_at=now
        )
        new_schedules.append(new_schedule)
    
    db.add_all(new_schedules)
    db.commit()
    
    return {"message": "Đã cập nhật lịch học thành công. Vui lòng chờ Giảng viên duyệt."}


@router.post("/{student_id}/approve")
def approve_student_schedule(
    student_id: str, 
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin)
):
    """Giảng viên duyệt lịch học của sinh viên."""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    pending_schedules = db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id, 
        StudentSchedule.is_approved == False,
        StudentSchedule.is_active == True
    ).all()
    
    if not pending_schedules:
        raise HTTPException(status_code=400, detail="Không có lịch học chờ duyệt.")
    
    # Tắt active của lịch học cũ đã duyệt (lưu vào lịch sử)
    db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id, 
        StudentSchedule.is_approved == True,
        StudentSchedule.is_active == True
    ).update({"is_active": False})
    
    now = datetime.now()
    for schedule in pending_schedules:
        schedule.is_approved = True
        schedule.approved_at = now
    
    db.commit()
    
    return {"message": "Đã duyệt lịch học thành công."}
