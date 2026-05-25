import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.schedule import StudentSchedule
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User

logger = logging.getLogger(__name__)

from datetime import time

SHIFTS = {
    1: {"start": time(7, 0), "end": time(9, 40)},
    2: {"start": time(9, 50), "end": time(12, 30)},
    3: {"start": time(13, 30), "end": time(16, 10)},
    4: {"start": time(16, 20), "end": time(19, 0)},
}

async def mark_absent_task():
    """
    Quét vào 23:59 mỗi ngày để đánh dấu vắng mặt:
    - Đối chiếu các phiên điểm danh với từng ca học đăng ký.
    - Thiếu ca nào sẽ bị đánh dấu vắng không phép ca đó.
    - Phiên nào quên check-out sẽ bị đánh dấu.
    """
    logger.info("Chạy tác vụ đánh dấu vắng mặt cuối ngày...")
    db: Session = SessionLocal()
    try:
        today = datetime.now()
        current_date = today.date()
        day_of_week = today.weekday()

        # Tìm tất cả lịch học đã được duyệt của ngày hôm nay
        schedules = db.query(StudentSchedule).filter(
            StudentSchedule.day_of_week == day_of_week,
            StudentSchedule.is_approved == True
        ).all()
        
        for schedule in schedules:
            user_id = schedule.user_id
            shift_ids = [int(s.strip()) for s in schedule.shifts.split(",") if s.strip().isdigit()]
            
            # Lấy tất cả bản ghi (phiên) điểm danh của sinh viên hôm nay
            attendances = db.query(Attendance).filter(
                Attendance.user_id == user_id,
                Attendance.attendance_date == current_date
            ).all()
            
            # Kiểm tra xem sinh viên có vắng ca học nào không
            for shift_id in shift_ids:
                if shift_id not in SHIFTS: continue
                shift_start = SHIFTS[shift_id]["start"]
                shift_end = SHIFTS[shift_id]["end"]
                
                is_present = False
                for att in attendances:
                    # Bỏ qua các bản ghi do hệ thống tự sinh (vắng mặt) hoặc không có check_in_time
                    if att.camera_id == "system_auto": continue
                    if not att.check_in_time: continue
                    
                    in_time = att.check_in_time.time()
                    out_time = att.check_out_time.time() if att.check_out_time else time(23, 59, 59)
                    
                    # Overlap: (in_time <= shift_end) and (shift_start <= out_time)
                    if in_time <= shift_end and shift_start <= out_time:
                        is_present = True
                        break
                        
                if not is_present:
                    new_att = Attendance(
                        user_id=user_id,
                        attendance_date=current_date,
                        confidence_score=0.0,
                        camera_id="system_auto",
                        status=AttendanceStatus.absent_unexcused,
                        override_reason=f"Vắng Ca {shift_id}"
                    )
                    db.add(new_att)

            # Cập nhật trạng thái "Quên check-out" cho các phiên mở
            for att in attendances:
                if att.camera_id != "system_auto" and att.check_out_time is None and att.status == AttendanceStatus.success:
                    att.status = AttendanceStatus.present_incomplete
                
        db.commit()
        logger.info("Đã hoàn tất đánh dấu vắng mặt tự động.")
    except Exception as e:
        logger.error(f"Lỗi khi chạy tác vụ quét vắng mặt: {e}")
        db.rollback()
    finally:
        db.close()

async def daily_scheduler_loop():
    """Vòng lặp chạy ngầm, kích hoạt vào 23:59 mỗi ngày."""
    while True:
        now = datetime.now()
        # Tính toán thời gian ngủ cho đến 23:59:00 hôm nay (hoặc ngày mai)
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        
        sleep_seconds = (target - now).total_seconds()
        logger.info(f"Scheduler sẽ ngủ {sleep_seconds} giây cho đến lần chạy tiếp theo lúc {target}")
        
        await asyncio.sleep(sleep_seconds)
        await mark_absent_task()

def start_scheduler():
    asyncio.create_task(daily_scheduler_loop())
