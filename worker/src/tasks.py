import logging
import os

from src.face_engine import FaceEngine
from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="extract_face_embedding_task")
def extract_face_embedding_task(image_url: str) -> dict:
	"""Extract face embedding vector from an image (used during registration)."""
	if not image_url:
		return {
			"status": "failed",
			"message": "Missing image URL.",
		}

	try:
		engine = FaceEngine()
		vector = engine.extract_vector(image_url)
		return {
			"status": "success",
			"vector": vector,
		}
	except Exception as exc:
		logger.error("Embedding extraction error: %s", exc)
		return {
			"status": "failed",
			"message": f"Embedding extraction error: {exc}",
		}


@celery_app.task(name="recognize_face_task")
def recognize_face_task(image_url: str, student_id: str = "") -> dict:
	"""Recognize a face from an image, filtered by student_id.

	Nhan dien khuon mat tu anh, loc theo student_id.

	Args:
		image_url: URL of the uploaded image in MinIO
		student_id: Student ID to filter Qdrant search

	Returns:
		dict with status, student_id, score, threshold, matched, reason, message
	"""
	threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.68"))

	if not image_url:
		return {
			"status": "failed",
			"student_id": student_id or "Unknown",
			"score": 0.0,
			"threshold": threshold,
			"matched": False,
			"reason": "Thiếu đường dẫn ảnh.",
			"message": "Thiếu đường dẫn ảnh.",
		}

	if not student_id:
		return {
			"status": "failed",
			"student_id": "Unknown",
			"score": 0.0,
			"threshold": threshold,
			"matched": False,
			"reason": "Thiếu mã sinh viên.",
			"message": "Thiếu mã sinh viên (student_id).",
		}

	try:
		engine = FaceEngine()

		# Step 1: Extract embedding (includes quality checks and face alignment)
		try:
			vector = engine.extract_vector(image_url)
		except ValueError as exc:
			# Quality check or face detection failure
			logger.warning("Image quality/detection error for student_id=%s: %s", student_id, exc)
			return {
				"status": "quality_error",
				"student_id": student_id,
				"score": 0.0,
				"threshold": threshold,
				"matched": False,
				"reason": str(exc),
				"message": str(exc),
			}

		# Step 2: Search Qdrant filtered by student_id
		match = engine.search_qdrant(vector, student_id)

		score = float(match.get("score", 0.0))
		matched = bool(match.get("matched", False))
		reason = match.get("reason", "")

		if matched:
			logger.info(
				"Recognition SUCCESS: student_id=%s, score=%.4f, threshold=%.4f",
				student_id, score, threshold,
			)
			return {
				"status": "success",
				"student_id": student_id,
				"score": score,
				"threshold": threshold,
				"matched": True,
				"reason": reason,
				"message": f"Nhận diện thành công (độ tương đồng {score:.4f}).",
			}

		logger.info(
			"Recognition FAILED: student_id=%s, score=%.4f, threshold=%.4f, reason=%s",
			student_id, score, threshold, reason,
		)
		return {
			"status": "failed",
			"student_id": student_id,
			"score": score,
			"threshold": threshold,
			"matched": False,
			"reason": reason,
			"message": f"Không khớp khuôn mặt (độ tương đồng {score:.4f}).",
		}

	except Exception as exc:
		logger.error("Recognition error for student_id=%s: %s", student_id, exc, exc_info=True)
		return {
			"status": "failed",
			"student_id": student_id,
			"score": 0.0,
			"threshold": threshold,
			"matched": False,
			"reason": f"Lỗi nhận diện: {exc}",
			"message": f"Lỗi nhận diện: {exc}",
		}
