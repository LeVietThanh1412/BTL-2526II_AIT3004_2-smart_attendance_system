from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemberRegistrationRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	name: str = Field(min_length=1, max_length=255)
	images_base64: list[str] = Field(min_length=1)


class MemberRegistrationResponse(BaseModel):
	student_id: str
	name: str
	embedding_dimension: int
	accepted_images: int
	stored_image_paths: list[str]
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)
