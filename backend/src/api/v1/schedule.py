from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import get_db
from src.models.user import User
from src.models.schedule import StudentSchedule
from src.schemas.schedule import ScheduleListUpdate, ScheduleResponse
from src.api.v1.auth import get_current_admin

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.get("/{student_id}", response_model=List[ScheduleResponse])
def get_student_schedule(student_id: str, db: Session = Depends(get_db)):
    """Lấy danh sách lịch học đã đăng ký của sinh viên"""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    return user.schedules

@router.post("/{student_id}")
def update_student_schedule(
    student_id: str, 
    payload: ScheduleListUpdate, 
    db: Session = Depends(get_db)
):
    """Cập nhật toàn bộ lịch học của sinh viên. Xóa lịch cũ và ghi đè bằng lịch mới."""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    # Xóa lịch cũ
    db.query(StudentSchedule).filter(StudentSchedule.user_id == user.id).delete()
    
    # Thêm lịch mới
    new_schedules = []
    for schedule_data in payload.schedules:
        new_schedule = StudentSchedule(
            user_id=user.id,
            day_of_week=schedule_data.day_of_week,
            shifts=schedule_data.shifts
        )
        new_schedules.append(new_schedule)
    
    db.add_all(new_schedules)
    db.commit()
    
    return {"message": "Đã cập nhật lịch học thành công."}
