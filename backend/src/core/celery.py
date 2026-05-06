from celery import Celery

from src.core.config import settings

class _CeleryTaskProxy:
    """
    Lớp Proxy cho các task Celery cho phép gửi task đến worker
    mà không cần định nghĩa trực tiếp hàm task trong module này.
    """
    def __init__(self, app: Celery, task_name: str) -> None:
        self.app = app
        self.task_name = task_name

    def delay(self, *args, **kwargs):
        """Send task to queue with specified arguments."""
        return self.app.send_task(self.task_name, args=args, kwargs=kwargs)


celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

extract_face_embedding_task = _CeleryTaskProxy(celery_app, "extract_face_embedding_task")

recognize_face_task = _CeleryTaskProxy(celery_app, "recognize_face_task")
