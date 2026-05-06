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
		return {
			"status": "failed",
			"student_id": "Unknown",
			"message": "Missing image URL.",
		}

	try:
		engine = FaceEngine()
		vector = engine.extract_vector(image_url)
		match = engine.search_qdrant(vector)

		score = float(match.get("score", 0.0))
		student_id = str(match.get("student_id", "Unknown"))

		if score > 0.6 and student_id != "Unknown":
			return {
				"status": "success",
				"student_id": student_id,
				"message": f"Face matched with score {score:.4f}.",
			}

		return {
			"status": "failed",
			"student_id": "Unknown",
			"message": f"No confident match found (score={score:.4f}).",
		}
	except Exception as exc:
		return {
			"status": "failed",
			"student_id": "Unknown",
			"message": f"Recognition error: {exc}",
		}
