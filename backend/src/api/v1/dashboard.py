"""
Dashboard API endpoints - statistics and recent activity.
API endpoints dashboard - thong ke va hoat dong gan day.
"""
from datetime import date, datetime
import math

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.core.config import settings
from src.database import get_db
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User

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
    statusColor: str  # "green" | "red" | "yellow"


class RecentActivitiesResponse(BaseModel):
    activities: list[ActivityItem]


class AttendanceLogItem(BaseModel):
    id: int
    student_id: str | None
    name: str
    time: str
    date: str
    status: str
    statusColor: str
    camera_id: str
    confidence_score: float


class AttendanceLogsResponse(BaseModel):
    items: list[AttendanceLogItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class NotificationResponse(BaseModel):
    count: int


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


def _fmt_date(dt: datetime) -> str:
    """Format a datetime as DD/MM/YYYY."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
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
        late = _is_late(attendance.check_in_time)
        return ("Đi muộn" if late else "Đúng giờ", "red" if late else "green")

    if attendance.status == AttendanceStatus.failed:
        return ("Không nhận diện", "red")

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
        func.hour(Attendance.check_in_time) < _LATE_HOUR,
        and_(
            func.hour(Attendance.check_in_time) == _LATE_HOUR,
            func.minute(Attendance.check_in_time) <= _LATE_MINUTE,
        ),
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
                time=_fmt_time(dt),
                date=_fmt_date(dt),
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
                time=_fmt_time(dt),
                date=_fmt_date(dt),
                status=status_label,
                statusColor=color,
                camera_id=attendance.camera_id,
                confidence_score=float(attendance.confidence_score or 0.0),
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
    Return unread notification count (late/unknown check-ins today).
    Tra ve so thong bao chua doc (diem danh muon / khong ro ngay hom nay).
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
        func.hour(Attendance.check_in_time) > _LATE_HOUR,
        and_(
            func.hour(Attendance.check_in_time) == _LATE_HOUR,
            func.minute(Attendance.check_in_time) > _LATE_MINUTE,
        ),
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

    return NotificationResponse(count=count + late_count)
