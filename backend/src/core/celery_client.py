"""
Celery configuration and task proxy declarations for asynchronous processing.
Cau hinh Celery va khai bao cac task proxy xu ly khong dong bo.

This is the SINGLE source of truth for Celery in the backend.
All modules should import celery_app and task proxies from here.
"""
from celery import Celery

from src.core.config import settings


class _CeleryTaskProxy:
    """
    Proxy class for Celery tasks that allows sending tasks to worker
    without direct task function definition in this module.
    
    Lop Proxy cho cac task Celery cho phep gui task den worker
    ma khong can dinh nghia truc tiep ham task trong module nay.
    """

    def __init__(self, app: Celery, task_name: str) -> None:
        self.app = app
        self.task_name = task_name

    def delay(self, *args, **kwargs):
        """Send task to queue with specified arguments."""
        return self.app.send_task(self.task_name, args=args, kwargs=kwargs)


# --- Single Celery app instance for the entire backend ---
celery_app = Celery(
    "smart_attendance",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# --- Task proxies ---
# Member registration: extract face embedding from an image
extract_face_embedding_task = _CeleryTaskProxy(celery_app, "extract_face_embedding_task")

# Attendance check-in: recognize a face from an image
recognize_face_task = _CeleryTaskProxy(celery_app, "recognize_face_task")
