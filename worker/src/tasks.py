import os

from src.face_engine import FaceEngine
from src.celery_app import celery_app


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
def recognize_face_task(image_url: str) -> dict:
	if not image_url:
		threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
		return {
			"status": "failed",
			"student_id": "Unknown",
			"score": 0.0,
			"threshold": threshold,
			"message": "Thiếu đường dẫn ảnh.",
		}

	try:
		threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
		engine = FaceEngine()
		vector = engine.extract_vector(image_url)
		match = engine.search_qdrant(vector)

		score = float(match.get("score", 0.0))
		student_id = str(match.get("student_id", "Unknown"))

		if score > threshold and student_id != "Unknown":
			return {
				"status": "success",
				"student_id": student_id,
				"score": score,
				"threshold": threshold,
				"message": f"Nhận diện thành công (độ tương đồng {score:.4f}).",
			}

		return {
			"status": "failed",
			"student_id": "Unknown",
			"score": score,
			"threshold": threshold,
			"message": f"Không tìm thấy khuôn mặt phù hợp (độ tương đồng {score:.4f}).",
		}
	except Exception as exc:
		threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.6"))
		return {
			"status": "failed",
			"student_id": "Unknown",
			"score": 0.0,
			"threshold": threshold,
			"message": f"Lỗi nhận diện: {exc}",
		}
