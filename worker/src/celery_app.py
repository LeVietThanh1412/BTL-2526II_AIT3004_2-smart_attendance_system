import logging
import os

from celery import Celery
from celery.signals import worker_ready

logger = logging.getLogger(__name__)

def _env(name: str, default: str) -> str:
	value = os.getenv(name)
	return value if value else default


celery_app = Celery(
	"attendance_worker",
	broker=_env("CELERY_BROKER_URL", "redis://redis:6379/0"),
	backend=_env("CELERY_RESULT_BACKEND", _env("CELERY_BROKER_URL", "redis://redis:6379/0")),
)

celery_app.conf.update(
	task_serializer="json",
	accept_content=["json"],
	result_serializer="json",
	timezone="UTC",
	enable_utc=True,
    imports=("src.tasks",),
    # Real-Time Protocol Configurations
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_expires=3600,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_connection_retry_on_startup=True,
)

@worker_ready.connect
def warmup_model(sender, **kwargs):
    """
    Pre-download and load DeepFace model on worker startup to avoid 
    cold-start latency on the first check-in request.
    """
    import numpy as np
    from deepface import DeepFace
    
    model = os.getenv("DEEPFACE_MODEL_NAME", "ArcFace")
    logger.info(f"Bat dau pre-warm model '{model}' tren worker...")
    
    try:
        # Pass a dummy zero image to force model load and weight initialization
        dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
        DeepFace.represent(
            img_path=dummy_img,
            model_name=model,
            enforce_detection=False,
            detector_backend="skip"
        )
        
        # Khởi tạo luôn Qdrant collection và FaceEngine
        from src.tasks import _get_engine
        _get_engine()
        
        logger.info(f"Khởi tạo xong AI Model '{model}' và Qdrant collection thành công.")
    except Exception as exc:
        logger.warning(f"Lỗi khi khởi tạo AI model: {exc}")
