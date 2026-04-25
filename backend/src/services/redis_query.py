import json

from redis import Redis
from redis.exceptions import RedisError

from src.core.config import settings


class RedisEmbeddingCache:
    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _key(student_id: str) -> str:
        return f"user:{student_id}:embedding"

    def set_embedding(self, student_id: str, embedding: list[float]) -> None:
        try:
            self.client.setex(
                self._key(student_id),
                settings.redis_embedding_ttl_seconds,
                json.dumps(embedding),
            )
        except RedisError:
            return

    def get_embedding(self, student_id: str) -> list[float] | None:
        try:
            value = self.client.get(self._key(student_id))
        except RedisError:
            return None

        if value is None:
            return None

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, list):
            return None

        return [float(x) for x in parsed]


redis_embedding_cache = RedisEmbeddingCache()
