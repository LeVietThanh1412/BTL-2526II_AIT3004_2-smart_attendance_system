from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreateRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	full_name: str = Field(min_length=1, max_length=255)


class UserCreateResponse(BaseModel):
	id: int
	student_id: str
	full_name: str
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)


# Backward-compatible aliases for existing imports.
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


class VideoMemberRegistrationRequest(BaseModel):
	"""Đăng ký sinh viên bằng video (Register student using video)"""
	student_id: str = Field(min_length=3, max_length=30)
	name: str = Field(min_length=1, max_length=255)


class VideoMemberRegistrationResponse(BaseModel):
	"""Phản hồi đăng ký video (Video registration response)"""
	student_id: str
	name: str
	embedding_dimension: int
	frames_processed: int
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)
