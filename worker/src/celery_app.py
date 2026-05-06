import os

from celery import Celery


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
)
