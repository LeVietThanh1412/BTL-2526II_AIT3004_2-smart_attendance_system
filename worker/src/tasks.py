import os

from src.face_engine import FaceEngine
from src.celery_app import celery_app


def _map_recognition_error(raw_message: str) -> str:
	message = raw_message or ""
	if message == "image_blurry":
		return "Ảnh bị mờ, vui lòng chụp lại rõ nét hơn."
	if message == "image_too_dark":
		return "Ảnh quá tối, vui lòng tăng ánh sáng."
	if message == "invalid_image":
		return "Ảnh không hợp lệ hoặc không đọc được."
	if "Face could not be detected" in message or "No face" in message:
		return "Không phát hiện khuôn mặt trong ảnh."
	return f"Lỗi nhận diện: {message}"


def _failure_payload(student_id: str, threshold: float, reason: str, score: float = 0.0) -> dict:
	return {
		"status": "failed",
		"student_id": student_id or "Unknown",
		"match_score": float(score),
		"score": float(score),
		"threshold": float(threshold),
		"matched": False,
		"reason": reason,
		"message": reason,
	}


@celery_app.task(name="extract_face_embedding_task")
def extract_face_embedding_task(image_url: str) -> dict:
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
		return {
			"status": "failed",
			"message": f"Embedding extraction error: {exc}",
		}


@celery_app.task(name="recognize_face_task")
def recognize_face_task(image_url: str, student_id: str) -> dict:
	threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
	student_id = str(student_id or "").strip()

	if not student_id:
		return _failure_payload("Unknown", threshold, "Thiếu mã sinh viên.")

	if not image_url:
		return _failure_payload(student_id, threshold, "Thiếu đường dẫn ảnh.")

	try:
		engine = FaceEngine()
		vector = engine.extract_vector(image_url)
		match = engine.search_qdrant(vector, student_id=student_id)

		score = float(match.get("score", 0.0))
		found = bool(match.get("found", False))

		if not found:
			return _failure_payload(student_id, threshold, "Không có vector khuôn mặt cho mã sinh viên này.")

		if score >= threshold:
			return {
				"status": "success",
				"student_id": student_id,
				"match_score": score,
				"score": score,
				"threshold": threshold,
				"matched": True,
				"reason": "Nhận diện thành công.",
				"message": f"Nhận diện thành công (độ tương đồng {score:.4f}).",
			}

		reason = f"Độ tương đồng thấp ({score:.4f} < {threshold:.4f})."
		return _failure_payload(student_id, threshold, reason, score)
	except Exception as exc:
		reason = _map_recognition_error(str(exc))
		return _failure_payload(student_id, threshold, reason)
