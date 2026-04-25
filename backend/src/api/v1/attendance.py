import json
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import settings
from src.database import get_db
from src.models.user import AttendanceLog, AttendanceStatus, User
from src.schemas.attendance import AttendanceVerifyRequest, AttendanceVerifyResponse
from src.services.face_ai import face_ai_service
from src.services.redis_query import redis_embedding_cache
from src.services.storages import storage_service


router = APIRouter(prefix="/attendance", tags=["attendance"])


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
	denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
	if denom == 0:
		return 0.0
	return float(np.dot(vec_a, vec_b) / denom)


@router.post("/verify", response_model=AttendanceVerifyResponse)
def verify_attendance(payload: AttendanceVerifyRequest, db: Session = Depends(get_db)):
	user = db.query(User).filter(User.student_id == payload.student_id).first()
	if user is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Student not found.",
		)

	master_embedding = redis_embedding_cache.get_embedding(payload.student_id)
	if master_embedding is None:
		if user.embedding is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="No registered facial embedding for this student.",
			)
		try:
			master_embedding = json.loads(user.embedding.embedding_vector)
		except json.JSONDecodeError as exc:
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Stored embedding is corrupted.",
			) from exc
		redis_embedding_cache.set_embedding(payload.student_id, master_embedding)

	current_embedding = face_ai_service.embedding_from_base64(payload.image_base64)
	similarity = cosine_similarity(
		np.array(master_embedding, dtype=np.float32),
		np.array(current_embedding, dtype=np.float32),
	)
	success = similarity >= settings.face_similarity_threshold

	captured_path = storage_service.save_image(
		payload.image_base64,
		payload.student_id,
		prefix="attendance",
	)

	attendance_log = AttendanceLog(
		user_id=user.id,
		similarity_score=similarity,
		status=AttendanceStatus.success if success else AttendanceStatus.failed,
		captured_image_path=captured_path,
	)
	db.add(attendance_log)
	db.commit()

	return AttendanceVerifyResponse(
		student_id=user.student_id,
		name=user.name,
		similarity_score=similarity,
		threshold=settings.face_similarity_threshold,
		success=success,
		timestamp=datetime.now(timezone.utc),
	)
