import json

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import settings
from src.database import get_db
from src.models.user import FaceEmbedding, User
from src.schemas.user import MemberRegistrationRequest, MemberRegistrationResponse
from src.services.face_ai import face_ai_service
from src.services.redis_query import redis_embedding_cache
from src.services.storages import storage_service


router = APIRouter(prefix="/members", tags=["members"])


@router.post("/register", response_model=MemberRegistrationResponse)
def register_member(payload: MemberRegistrationRequest, db: Session = Depends(get_db)):
	if len(payload.images_base64) < settings.min_registration_images:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"At least {settings.min_registration_images} images are required for registration.",
		)

	embeddings: list[np.ndarray] = []
	stored_image_paths: list[str] = []

	for image_b64 in payload.images_base64:
		image_path = storage_service.save_image(image_b64, payload.student_id, prefix="register")
		stored_image_paths.append(image_path)

		try:
			emb = face_ai_service.embedding_from_base64(image_b64)
			embeddings.append(emb)
		except HTTPException:
			continue

	if not embeddings:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="No valid face embedding generated from registration images.",
		)

	master_embedding = np.mean(np.stack(embeddings), axis=0)
	master_embedding_list = master_embedding.astype(float).tolist()

	user = db.query(User).filter(User.student_id == payload.student_id).first()
	if user is None:
		user = User(student_id=payload.student_id, name=payload.name)
		db.add(user)
		db.flush()
	else:
		user.name = payload.name

	if user.embedding is None:
		embedding_row = FaceEmbedding(
			user_id=user.id,
			embedding_vector=json.dumps(master_embedding_list),
			image_paths=json.dumps(stored_image_paths),
		)
		db.add(embedding_row)
	else:
		user.embedding.embedding_vector = json.dumps(master_embedding_list)
		user.embedding.image_paths = json.dumps(stored_image_paths)

	db.commit()
	db.refresh(user)

	redis_embedding_cache.set_embedding(payload.student_id, master_embedding_list)

	return MemberRegistrationResponse(
		student_id=user.student_id,
		name=user.name,
		embedding_dimension=len(master_embedding_list),
		accepted_images=len(embeddings),
		stored_image_paths=stored_image_paths,
		created_at=user.created_at,
	)
