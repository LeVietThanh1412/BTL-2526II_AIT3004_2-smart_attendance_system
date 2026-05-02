"""
Redis-backed embedding cache for fast attendance lookups.

The actual face-AI pipeline (extract embedding, compare) runs in the Celery
worker.  The backend only reads/writes the cache so it can serve results
quickly via the /attendance/result endpoint.
"""
import json

from redis import Redis
from redis.exceptions import RedisError

from src.core.config import settings

_RESULT_PREFIX = "attendance:result:"
_EMBED_PREFIX = "user:{student_id}:embedding"


class AttendanceResultCache:
    """Store/retrieve task results in Redis so the frontend can poll."""

    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def set_result(self, task_id: str, data: dict, ttl: int = 300) -> None:
        try:
            self.client.setex(f"{_RESULT_PREFIX}{task_id}", ttl, json.dumps(data))
        except RedisError:
            pass

    def get_result(self, task_id: str) -> dict | None:
        try:
            raw = self.client.get(f"{_RESULT_PREFIX}{task_id}")
        except RedisError:
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None


attendance_result_cache = AttendanceResultCache()
