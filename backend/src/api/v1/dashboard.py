"""
Dashboard API endpoints - statistics and recent activity.
API endpoints dashboard - thong ke va hoat dong gan day.
"""
from datetime import date, datetime
import math
import io
import csv

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.core.config import settings
from src.database import get_db
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User
from src.models.schedule import StudentSchedule

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ─── Response schemas ─────────────────────────────────────────────────────────

class StatisticsResponse(BaseModel):
    total: int
    missing: int
    onTime: int
    late: int


class ActivityItem(BaseModel):
    name: str
    time: str
    date: str
    status: str
    statusColor: str


class RecentActivitiesResponse(BaseModel):
    activities: list[ActivityItem]


class AttendanceLogItem(BaseModel):
    id: int
    student_id: str | None
    name: str
    time: str
    date: str
    check_out_time: str | None = None
    status: str
    statusColor: str
    raw_status: str
    camera_id: str
    confidence_score: float
    is_late_override: bool | None = None
    override_reason: str | None = None


class AttendanceLogsResponse(BaseModel):
    items: list[AttendanceLogItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class NotificationResponse(BaseModel):
    count: int


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    time: str
    date: str
    route: str



# Threshold (local time) that separates "on-time" from "late".
# Students checking in after TIME_LATE are considered late.
def _parse_late_time(raw_value: str) -> tuple[int, int]:
    value = (raw_value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt).time()
            return (parsed.hour, parsed.minute)
        except ValueError:
            continue

    return (8, 0)


_LATE_HOUR, _LATE_MINUTE = _parse_late_time(settings.time_late)


def _fmt_time(dt: datetime) -> str:
    """Format a datetime as HH:MM:SS (local naive or UTC-aware)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt.strftime("%H:%M:%S")


def _fmt_date(dt: date | datetime) -> str:
    """Format a date/datetime as DD/MM/YYYY."""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt.strftime("%d/%m/%Y")
    # `date` has no tzinfo; keep it simple.
    return dt.strftime("%d/%m/%Y")


def _is_late(dt: datetime) -> bool:
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)

    if dt.hour > _LATE_HOUR:
        return True
    if dt.hour < _LATE_HOUR:
        return False
    return dt.minute > _LATE_MINUTE


def _build_status(attendance: Attendance) -> tuple[str, str]:
    if attendance.status == AttendanceStatus.success:
        if attendance.is_late_override is not None:
            late = attendance.is_late_override
        else:
            late = _is_late(attendance.check_in_time)
            
        if late:
            return ("Hoàn thành (Muộn)" if attendance.check_out_time else "Vào muộn", "yellow")
        
        return ("Hoàn thành" if attendance.check_out_time else "Vào đúng giờ", "green")

    if attendance.status == AttendanceStatus.failed:
        return ("Nhận diện lỗi / Thất bại", "red")
        
    if attendance.status == AttendanceStatus.absent_unexcused:
        return ("Vắng không phép", "red")
        
    if attendance.status == AttendanceStatus.absent_excused:
        return ("Vắng có phép", "yellow")
        
    if attendance.status == AttendanceStatus.present_incomplete:
        return ("Quên check-out", "yellow")

    return ("Không xác định", "yellow")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/statistics", response_model=StatisticsResponse)
def get_statistics(db: Session = Depends(get_db)):
    """
    Return today's attendance statistics.
    Tra ve thong ke diem danh trong ngay hom nay.
    """
    today = date.today()

    total_members = db.query(func.count(User.id)).scalar() or 0

    # Distinct users who checked in successfully today
    checked_in_ids = (
        db.query(Attendance.user_id)
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status == AttendanceStatus.success,
            Attendance.user_id.isnot(None),
        )
        .distinct()
        .subquery()
    )

    checked_in_count = db.query(func.count()).select_from(checked_in_ids).scalar() or 0
    missing_count = max(0, total_members - checked_in_count)

    on_time_filter = or_(
        Attendance.is_late_override == False,
        and_(
            Attendance.is_late_override.is_(None),
            or_(
                func.hour(Attendance.check_in_time) < _LATE_HOUR,
                and_(
                    func.hour(Attendance.check_in_time) == _LATE_HOUR,
                    func.minute(Attendance.check_in_time) <= _LATE_MINUTE,
                ),
            )
        )
    )

    # On-time: checked in before or at TIME_LATE
    on_time_ids = (
        db.query(Attendance.user_id)
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status == AttendanceStatus.success,
            Attendance.user_id.isnot(None),
            on_time_filter,
        )
        .distinct()
        .subquery()
    )
    on_time_count = db.query(func.count()).select_from(on_time_ids).scalar() or 0
    late_count = max(0, checked_in_count - on_time_count)

    return StatisticsResponse(
        total=total_members,
        missing=missing_count,
        onTime=on_time_count,
        late=late_count,
    )


@router.get("/recent-activities", response_model=RecentActivitiesResponse)
def get_recent_activities(limit: int = 10, db: Session = Depends(get_db)):
    """
    Return the most recent attendance check-in records.
    Tra ve cac ban ghi diem danh gan nhat.
    """
    rows = (
        db.query(Attendance, User)
        .outerjoin(User, Attendance.user_id == User.id)
        .order_by(Attendance.check_in_time.desc())
        .limit(limit)
        .all()
    )

    items: list[ActivityItem] = []
    for attendance, user in rows:
        dt: datetime = attendance.check_in_time
        display_name = user.full_name if user else f"ID: {attendance.user_id or 'Unknown'}"

        status_label, color = _build_status(attendance)

        items.append(
            ActivityItem(
                name=display_name,
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else _fmt_date(attendance.attendance_date),
                status=status_label,
                statusColor=color,
            )
        )

    return RecentActivitiesResponse(activities=items)


@router.get("/attendance-logs", response_model=AttendanceLogsResponse)
def get_attendance_logs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """
    Return paginated attendance logs (all records).
    Tra ve danh sach log diem danh co phan trang.
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    total = db.query(func.count(Attendance.id)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    rows = (
        db.query(Attendance, User)
        .outerjoin(User, Attendance.user_id == User.id)
        .order_by(Attendance.check_in_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: list[AttendanceLogItem] = []
    for attendance, user in rows:
        dt: datetime = attendance.check_in_time
        display_name = user.full_name if user else "Không rõ"
        display_student_id = user.student_id if user else None
        status_label, color = _build_status(attendance)

        items.append(
            AttendanceLogItem(
                id=attendance.id,
                student_id=display_student_id,
                name=display_name,
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else _fmt_date(attendance.attendance_date),
                check_out_time=_fmt_time(attendance.check_out_time) if attendance.check_out_time else None,
                status=status_label,
                statusColor=color,
                raw_status=attendance.status.value,
                camera_id=attendance.camera_id,
                confidence_score=float(attendance.confidence_score or 0.0),
                is_late_override=attendance.is_late_override,
                override_reason=attendance.override_reason,
            )
        )

    return AttendanceLogsResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/notifications", response_model=NotificationResponse)
def get_notifications(db: Session = Depends(get_db)):
    """
    Return unread notification count (late/unknown check-ins today, pending users, pending schedules).
    Tra ve so thong bao chua doc (diem danh muon / khong ro ngay hom nay, sv moi dang ky, doi ca).
    """
    today = date.today()

    count = (
        db.query(func.count(Attendance.id))
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status != AttendanceStatus.success,
        )
        .scalar()
        or 0
    )

    late_filter = or_(
        Attendance.is_late_override == True,
        and_(
            Attendance.is_late_override.is_(None),
            or_(
                func.hour(Attendance.check_in_time) > _LATE_HOUR,
                and_(
                    func.hour(Attendance.check_in_time) == _LATE_HOUR,
                    func.minute(Attendance.check_in_time) > _LATE_MINUTE,
                ),
            )
        )
    )

    # Also count users who checked in late
    late_count = (
        db.query(func.count(Attendance.id))
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status == AttendanceStatus.success,
            late_filter,
        )
        .scalar()
        or 0
    )


    # Count pending users
    pending_users_count = (
        db.query(func.count(User.id))
        .filter(User.is_approved == False)
        .scalar()
        or 0
    )

    # Count pending schedules
    pending_schedules_count = (
        db.query(func.count(StudentSchedule.id))
        .filter(StudentSchedule.is_approved == False)
        .scalar()
        or 0
    )

    return NotificationResponse(
        count=count + late_count + pending_users_count + pending_schedules_count
    )


@router.get("/notifications/list", response_model=list[NotificationItem])
def get_notifications_list(db: Session = Depends(get_db)):
    """
    Return today's unread notifications details (late/unknown check-ins today, pending users, pending schedules).
    Danh sach chi tiet thong bao (diem danh muon/loi trong ngay, sv moi, doi ca).
    """
    today = date.today()
    items: list[NotificationItem] = []

    # 1. Today's failed check-ins
    failed_rows = (
        db.query(Attendance, User)
        .outerjoin(User, Attendance.user_id == User.id)
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status != AttendanceStatus.success,
        )
        .all()
    )
    for attendance, user in failed_rows:
        dt: datetime = attendance.check_in_time
        display_name = user.full_name if user else "Không xác định"
        items.append(
            NotificationItem(
                id=f"att_failed_{attendance.id}",
                type="attendance_failed",
                title="Điểm danh thất bại",
                message=f"Khuôn mặt không khớp hoặc lỗi chụp ảnh: {display_name}",
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else _fmt_date(attendance.attendance_date),
                route="/admin/attendance-logs",
            )
        )

    # 2. Today's late check-ins
    late_filter = or_(
        Attendance.is_late_override == True,
        and_(
            Attendance.is_late_override.is_(None),
            or_(
                func.hour(Attendance.check_in_time) > _LATE_HOUR,
                and_(
                    func.hour(Attendance.check_in_time) == _LATE_HOUR,
                    func.minute(Attendance.check_in_time) > _LATE_MINUTE,
                ),
            )
        )
    )
    late_rows = (
        db.query(Attendance, User)
        .outerjoin(User, Attendance.user_id == User.id)
        .filter(
            func.date(Attendance.check_in_time) == today,
            Attendance.status == AttendanceStatus.success,
            late_filter,
        )
        .all()
    )
    for attendance, user in late_rows:
        dt: datetime = attendance.check_in_time
        display_name = user.full_name if user else "Không xác định"
        items.append(
            NotificationItem(
                id=f"att_late_{attendance.id}",
                type="attendance_late",
                title="Điểm danh muộn",
                message=f"Sinh viên {display_name} điểm danh muộn ca học",
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else _fmt_date(attendance.attendance_date),
                route="/admin/attendance-logs",
            )
        )

    # 3. Pending users
    pending_users = (
        db.query(User)
        .filter(User.is_approved == False)
        .order_by(User.created_at.desc())
        .all()
    )
    for user in pending_users:
        dt: datetime = user.created_at
        items.append(
            NotificationItem(
                id=f"usr_pending_{user.id}",
                type="new_student",
                title="Yêu cầu đăng ký mới",
                message=f"Sinh viên {user.full_name} ({user.student_id}) đang chờ phê duyệt",
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else "--/--/----",
                route="/admin/members",
            )
        )

    # 4. Pending schedules
    pending_schedules = (
        db.query(StudentSchedule, User)
        .join(User, StudentSchedule.user_id == User.id)
        .filter(StudentSchedule.is_approved == False)
        .order_by(StudentSchedule.created_at.desc())
        .all()
    )
    for schedule, user in pending_schedules:
        dt: datetime = schedule.created_at
        items.append(
            NotificationItem(
                id=f"sch_pending_{schedule.id}",
                type="schedule_change",
                title="Yêu cầu đổi ca học",
                message=f"Sinh viên {user.full_name} ({user.student_id}) yêu cầu đổi ca học",
                time=_fmt_time(dt) if dt else "--:--",
                date=_fmt_date(dt) if dt else "--/--/----",
                route=f"/admin/schedule?student_id={user.student_id}",
            )
        )

    # Parse and sort all items by date & time descending
    def get_sort_key(item: NotificationItem):
        try:
            dt_str = f"{item.date} {item.time}"
            return datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
        except Exception:
            return datetime.min

    items.sort(key=get_sort_key, reverse=True)
    return items


@router.get("/export-attendance")
def export_attendance_logs(db: Session = Depends(get_db)):
    """
    Export all attendance logs as CSV.
    Xuat danh sach diem danh ra file CSV.
    """
    rows = (
        db.query(Attendance, User)
        .outerjoin(User, Attendance.user_id == User.id)
        .order_by(Attendance.check_in_time.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Ma SV", "Ho Ten", "Thoi Gian Vao", "Thoi Gian Ra", "Ngay", "Trang Thai", "Camera", "Do Chinh Xac"])

    def iter_csv():
        yield output.getvalue().encode('utf-8-sig') # BOM for Excel
        output.seek(0)
        output.truncate(0)

        for attendance, user in rows:
            dt: datetime = attendance.check_in_time
            display_name = user.full_name if user else "Khong ro"
            display_student_id = user.student_id if user else ""
            status_label, _ = _build_status(attendance)

            writer.writerow([
                attendance.id,
                display_student_id,
                display_name,
                _fmt_time(dt) if dt else "--:--",
                _fmt_time(attendance.check_out_time) if attendance.check_out_time else "--:--",
                _fmt_date(dt) if dt else _fmt_date(attendance.attendance_date),
                status_label + (f" ({attendance.override_reason})" if attendance.override_reason else ""),
                attendance.camera_id,
                f"{float(attendance.confidence_score or 0.0):.4f}"
            ])
            yield output.getvalue().encode('utf-8-sig')
            output.seek(0)
            output.truncate(0)

    headers = {
        "Content-Disposition": "attachment; filename=attendance_logs.csv"
    }
    return StreamingResponse(iter_csv(), media_type="text/csv", headers=headers)

