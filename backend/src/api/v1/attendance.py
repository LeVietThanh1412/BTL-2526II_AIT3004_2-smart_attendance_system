import logging

from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from pydantic import BaseModel

from src.core.celery_client import recognize_face_task
from src.core.config import settings
from src.core.qdrant_client import has_vectors_for_student
from src.database import get_db
from src.models.attendance import Attendance, AttendanceStatus
from src.models.user import User
from src.schemas.attendance import AttendanceCheckResponse
from src.services.storages import minio_service
from src.api.v1.auth import get_current_admin

from src.models.schedule import StudentSchedule
from datetime import datetime, time, timedelta

logger = logging.getLogger(__name__)

SHIFTS = {
    1: {"start": time(7, 0), "end": time(9, 40)},
    2: {"start": time(9, 50), "end": time(12, 30)},
    3: {"start": time(13, 30), "end": time(16, 10)},
    4: {"start": time(16, 20), "end": time(19, 0)},
}

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in", response_model=AttendanceCheckResponse)
async def check_in(
    image: UploadFile = File(...),
    student_id: str = Form(..., min_length=3, max_length=30),
    camera_id: str = Form(default=settings.default_camera_id),
    db: Session = Depends(get_db),
):
    """Điểm danh bằng hình ảnh chụp từ camera kèm mã sinh viên.

    Các bước:
    1. Kiểm tra student_id có tồn tại trong database không
    2. Lấy vector khuôn mặt tham chiếu (Redis cache → Qdrant fallback)
    3. Kiểm tra định dạng ảnh
    4. Tải ảnh lên MinIO storage
    5. Gửi tới worker cùng reference_vector để so sánh trực tiếp 1-1
    6. Trả về kết quả điểm danh với điểm khớp (match_score), ngưỡng, trạng thái khớp và lý do"""

    # --- Bước 1: Kiểm tra student_id có tồn tại trong database ---
    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        logger.warning("Check-in failed: student_id=%s not found in database", student_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã sinh viên '{student_id}' không tồn tại trong hệ thống.",
        )
    if not user.is_approved:
        logger.warning("Check-in failed: student_id=%s is not approved yet", student_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sinh viên '{student_id}' chưa được Giảng viên duyệt.",
        )

    # --- Kiểm tra lịch học ---
    today = datetime.now()
    current_date = today.date()
    current_time = today.time()
    day_of_week = today.weekday()
    
    schedule = db.query(StudentSchedule).filter(
        StudentSchedule.user_id == user.id,
        StudentSchedule.day_of_week == day_of_week,
        StudentSchedule.is_approved == True,
        StudentSchedule.is_active == True
    ).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không có lịch học đã được duyệt trong ngày hôm nay.",
        )

    # --- Bước 2: Kiểm tra sinh viên đã đăng ký khuôn mặt trên Qdrant chưa ---
    if not has_vectors_for_student(student_id):
        logger.warning("Check-in failed: student_id=%s has no face vectors", student_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sinh viên '{student_id}' chưa đăng ký khuôn mặt. Vui lòng đăng ký trước.",
        )

    # --- Bước 3: Kiểm tra định dạng ảnh ---
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên phải là hình ảnh (jpg, png, webp, ...).",
        )

    # --- Bước 4: Tải lên MinIO ---
    file_bytes = await image.read()
    minio_url = minio_service.upload_image(
        file_bytes=file_bytes,
        filename=image.filename or "capture.jpg",
    )

    # --- Bước 5: Gửi thông tin tới worker để xử lý ---
    async_result = recognize_face_task.delay(minio_url, student_id)

    try:
        worker_result = async_result.get(timeout=15)
    except CeleryTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Hết thời gian chờ nhận dạng khuôn mặt. Worker AI chưa phản hồi.",
        ) from exc
    except Exception as exc:
        logger.error("Worker error for student_id=%s: %s", student_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Worker nhận dạng khuôn mặt gặp lỗi. Vui lòng thử lại.",
        ) from exc

    # --- Bước 6: Xử lý kết quả trả về từ worker ---
    if not isinstance(worker_result, dict):
        worker_result = {
            "status": "failed",
            "student_id": student_id,
            "score": 0.0,
            "threshold": settings.face_similarity_threshold,
            "matched": False,
            "reason": str(worker_result),
            "message": str(worker_result),
        }

    status_value = str(worker_result.get("status", "failed")).lower()
    score = float(worker_result.get("score") or 0.0)
    threshold = float(worker_result.get("threshold") or settings.face_similarity_threshold)
    matched = bool(worker_result.get("matched", False))
    reason = worker_result.get("reason", "")
    message = worker_result.get("message", f"Điểm danh hoàn tất từ camera {camera_id}.")

    # --- Parse ca học hợp lệ (phải thực hiện trước _reject_with_score) ---
    shift_ids = [int(s.strip()) for s in schedule.shifts.split(",") if s.strip().isdigit() and int(s.strip()) in SHIFTS]
    if not shift_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lịch học bị lỗi định dạng hoặc chứa ca không hợp lệ.")

    first_shift = min(shift_ids)
    last_shift = max(shift_ids)
    shift_start_time = SHIFTS[first_shift]["start"]   # Giờ bắt đầu ca đầu tiên
    end_time_of_last_shift = SHIFTS[last_shift]["end"] # Giờ kết thúc ca cuối

    def _reject_with_score(error_message: str, t_start=None, t_end=None):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "failed",
                "student_id": student_id,
                "match_score": score,
                "threshold": threshold,
                "matched": matched,
                "reason": reason,
                "message": error_message,
                "action": "check_in",
                "shift_start": t_start.strftime("%H:%M") if t_start else shift_start_time.strftime("%H:%M"),
                "shift_end": t_end.strftime("%H:%M") if t_end else end_time_of_last_shift.strftime("%H:%M"),
            },
        )

    # Xác định trạng thái điểm danh
    if matched and status_value == "success":
        status_enum = AttendanceStatus.success
    elif status_value == "quality_error":
        status_enum = AttendanceStatus.failed
    else:
        status_enum = AttendanceStatus.failed

    # Ghi log kết quả để debug
    logger.info(
        "Check-in result: student_id=%s, match_score=%.4f, threshold=%.4f, matched=%s, reason=%s",
        student_id, score, threshold, matched, reason,
    )

    # Ràng buộc thời gian hệ thống
    if current_time < time(5, 30):
        return _reject_with_score("Hệ thống điểm danh chỉ mở từ 5h30 sáng.")

    # Lấy bản ghi attendance thành công gần nhất của user hôm nay
    attendance = db.query(Attendance).filter(
        Attendance.user_id == user.id,
        Attendance.attendance_date == current_date,
        Attendance.status == AttendanceStatus.success
    ).order_by(Attendance.check_in_time.desc()).first()

    # Bỏ block chặn check-in nhiều lần
    pass

    action = None
    is_late = None
    check_in_str = None
    check_out_str = None

    if not attendance or attendance.check_out_time is not None:
        # === CHECK-IN MỚI ===
        action = "check_in"

        # Xác định ca học mục tiêu thực tế cho phiên check-in này
        target_shift_id = None
        target_shift_start = None
        target_shift_end = None
        target_checkin_earliest = None
        
        for sid in sorted(shift_ids):
            s_start = SHIFTS[sid]["start"]
            s_end = SHIFTS[sid]["end"]
            c_earliest = (datetime.combine(current_date, s_start) - timedelta(minutes=30)).time()
            
            # Khung giờ check-in: Từ 30p trước ca đến khi ca kết thúc
            if current_time >= c_earliest and current_time <= s_end:
                target_shift_id = sid
                target_shift_start = s_start
                target_shift_end = s_end
                target_checkin_earliest = c_earliest
                break
                
        if not target_shift_id:
            first_earliest = (datetime.combine(current_date, shift_start_time) - timedelta(minutes=30)).time()
            if current_time < first_earliest:
                return _reject_with_score(
                    f"Chưa đến giờ học. Ca bắt đầu lúc {shift_start_time.strftime('%H:%M')}, có thể check-in sớm nhất lúc {first_earliest.strftime('%H:%M')}."
                )
            if current_time > end_time_of_last_shift:
                return _reject_with_score("Tất cả các ca học của bạn hôm nay đã kết thúc, không thể check-in.")
            
            return _reject_with_score("Hiện tại không nằm trong khung giờ mở điểm danh của bất kỳ ca học nào bạn đăng ký.")

        # Xác định đi muộn (15 phút sau khi ca bắt đầu)
        late_threshold = (datetime.combine(current_date, target_shift_start) + timedelta(minutes=15)).time()
        is_late = current_time > late_threshold

        if status_enum != AttendanceStatus.success:
            failed_attendance = Attendance(
                user_id=user.id,
                attendance_date=current_date,
                check_in_time=today,
                confidence_score=score,
                camera_id=camera_id,
                status=status_enum,
                snapshot_student_id=user.student_id,
                snapshot_full_name=user.full_name,
            )
            db.add(failed_attendance)
            try:
                db.commit()
            except Exception:
                db.rollback()
            return AttendanceCheckResponse(
                status=status_value,
                student_id=student_id,
                student_name=user.full_name,
                match_score=score,
                threshold=threshold,
                matched=matched,
                reason=reason,
                message=f"Check-in thất bại: {reason or 'Nhận diện khuôn mặt không thành công.'}",
                action=action,
                shift_start=target_shift_start.strftime("%H:%M") if target_shift_start else shift_start_time.strftime("%H:%M"),
                shift_end=target_shift_end.strftime("%H:%M") if target_shift_end else end_time_of_last_shift.strftime("%H:%M"),
            )

        attendance = Attendance(
            user_id=user.id,
            attendance_date=current_date,
            check_in_time=today,
            confidence_score=score,
            camera_id=camera_id,
            status=status_enum,
            is_late_override=is_late,
            snapshot_student_id=user.student_id,
            snapshot_full_name=user.full_name,
        )
        late_text = " (Muộn ⚠️)" if is_late else ""
        message = f"Check-in thành công lúc {today.strftime('%H:%M:%S')}{late_text}."
        check_in_str = today.strftime("%H:%M:%S")
        db.add(attendance)

    else:
        # === CHECK-OUT ===
        action = "check_out"

        # Ràng buộc: chỉ checkout trong 30 phút trước giờ tan ca của CA HIỆN TẠI (dựa vào check_in_time)
        check_in_t = attendance.check_in_time.time()
        target_shift = shift_ids[-1]
        for s in shift_ids:
            if check_in_t <= SHIFTS[s]["end"]:
                target_shift = s
                break
                
        target_shift_end_time = SHIFTS[target_shift]["end"]

        checkout_window_start = (
            datetime.combine(current_date, target_shift_end_time) - timedelta(minutes=30)
        ).time()
        
        # Cho phép check-out muộn 30 phút sau khi ca kết thúc
        checkout_window_end = (
            datetime.combine(current_date, target_shift_end_time) + timedelta(minutes=30)
        ).time()
        
        if current_time < checkout_window_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chưa đến giờ tan ca hiện tại. Chỉ được check-out trong 30 phút cuối (từ {checkout_window_start.strftime('%H:%M')}, tan lúc {target_shift_end_time.strftime('%H:%M')})."
            )
        if current_time > checkout_window_end:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Đã quá hạn check-out của ca học này (hạn cuối {checkout_window_end.strftime('%H:%M')})."
            )

        is_late = bool(attendance.is_late_override)

        if status_enum != AttendanceStatus.success:
            failed_log = Attendance(
                user_id=user.id,
                attendance_date=current_date,
                check_out_time=today,
                confidence_score=score,
                camera_id=camera_id,
                status=status_enum,
                snapshot_student_id=user.student_id,
                snapshot_full_name=user.full_name,
            )
            db.add(failed_log)
            message = f"Check-out thất bại: {reason or 'Nhận diện khuôn mặt không thành công.'}"
        else:
            attendance.check_out_time = today
            attendance.status = AttendanceStatus.success
            attendance.confidence_score = score
            attendance.camera_id = camera_id
            check_in_str = attendance.check_in_time.strftime("%H:%M:%S") if attendance.check_in_time else None
            check_out_str = today.strftime("%H:%M:%S")
            late_text = " | Đã vào muộn ⚠️" if is_late else ""
            message = f"Check-out thành công lúc {today.strftime('%H:%M:%S')}{late_text}."

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu log điểm danh. Vui lòng thử lại.",
        ) from exc

    return AttendanceCheckResponse(
        status=status_value,
        student_id=student_id,
        student_name=user.full_name,
        match_score=score,
        threshold=threshold,
        matched=matched,
        reason=reason,
        message=str(message),
        action=action,
        is_late=is_late,
        check_in_time=check_in_str,
        check_out_time=check_out_str,
        shift_start=target_shift_start.strftime("%H:%M") if 'target_shift_start' in locals() and target_shift_start else shift_start_time.strftime("%H:%M"),
        shift_end=target_shift_end_time.strftime("%H:%M") if 'target_shift_end_time' in locals() and target_shift_end_time else (target_shift_end.strftime("%H:%M") if 'target_shift_end' in locals() and target_shift_end else end_time_of_last_shift.strftime("%H:%M")),
    )


class OverrideRequest(BaseModel):
    status: str
    is_late_override: bool
    override_reason: str


@router.put("/{attendance_id}/override")
def override_late_status(
    attendance_id: int,
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin)
):
    """
    Giảng viên sửa đổi trạng thái đi muộn của bản ghi điểm danh
    """
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi điểm danh.")
    
    attendance.is_late_override = payload.is_late_override
    attendance.override_reason = payload.override_reason
    if payload.status in [e.value for e in AttendanceStatus]:
        new_status = AttendanceStatus(payload.status)
        attendance.status = new_status
        
        # Cleanup timestamps based on new status
        if new_status in [AttendanceStatus.absent_unexcused, AttendanceStatus.absent_excused, AttendanceStatus.failed]:
            attendance.check_in_time = None
            attendance.check_out_time = None
        elif new_status == AttendanceStatus.present_incomplete:
            attendance.check_out_time = None
            
    db.commit()
    
    return {"message": "Đã sửa trạng thái điểm danh thành công."}


# Các endpoint cũ (giữ lại dưới dạng comment để tham khảo)
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
