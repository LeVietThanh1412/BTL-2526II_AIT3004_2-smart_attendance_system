import logging
import os

from src.face_engine import FaceEngine
from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="extract_face_embedding_task")
def extract_face_embedding_task(image_url: str) -> dict:
	"""Trích xuất embedding khuôn mặt từ ảnh (dùng khi đăng ký)."""
	if not image_url:
		return {
			"status": "failed",
			"message": "Thiếu đường dẫn ảnh.",
		}

	try:
		engine = FaceEngine()
		vector = engine.extract_vector(image_url)
		return {
			"status": "success",
			"vector": vector,
		}
	except Exception as exc:
		logger.error("Lỗi trích xuất embedding: %s", exc)
		return {
			"status": "failed",
			"message": f"Lỗi trích xuất embedding: {exc}",
		}


@celery_app.task(name="recognize_face_task")
def recognize_face_task(image_url: str, student_id: str = "") -> dict:
	"""Nhận diện khuôn mặt từ ảnh, lọc theo student_id.

	Tham số:
		image_url: URL ảnh đã tải lên trong MinIO
		student_id: Mã sinh viên để lọc tìm kiếm trong Qdrant

	Trả về:
		dict gồm status, student_id, score, threshold, matched, reason, message
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

		# Bước 1: Trích xuất embedding (gồm kiểm tra chất lượng và căn chỉnh khuôn mặt)
		try:
			vector = engine.extract_vector(image_url)
		except ValueError as exc:
			# Lỗi kiểm tra chất lượng hoặc phát hiện khuôn mặt
			logger.warning("Lỗi chất lượng ảnh/phát hiện khuôn mặt cho student_id=%s: %s", student_id, exc)
			return {
				"status": "quality_error",
				"student_id": student_id,
				"score": 0.0,
				"threshold": threshold,
				"matched": False,
				"reason": str(exc),
				"message": str(exc),
			}

		# Bước 2: Tìm kiếm Qdrant theo student_id
		match = engine.search_qdrant(vector, student_id)

		score = float(match.get("score", 0.0))
		matched = bool(match.get("matched", False))
		reason = match.get("reason", "")

		if matched:
			logger.info(
				"Nhận diện THÀNH CÔNG: student_id=%s, score=%.4f, threshold=%.4f",
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
			"Nhận diện THẤT BẠI: student_id=%s, score=%.4f, threshold=%.4f, reason=%s",
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
		logger.error("Lỗi nhận diện cho student_id=%s: %s", student_id, exc, exc_info=True)
		return {
			"status": "failed",
			"student_id": student_id,
			"score": 0.0,
			"threshold": threshold,
			"matched": False,
			"reason": f"Lỗi nhận diện: {exc}",
			"message": f"Lỗi nhận diện: {exc}",
		}
