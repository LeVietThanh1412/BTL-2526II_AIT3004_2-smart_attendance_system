from pydantic import BaseModel, Field

from src.core.config import settings


class AttendanceCheckRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	camera_id: str = Field(default=settings.default_camera_id, min_length=1, max_length=50)


class AttendanceCheckResponse(BaseModel):
	status: str
	student_id: str
	match_score: float
	threshold: float
	matched: bool
	reason: str
	message: str | None = None


class AttendanceVerifyRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	image_base64: str = Field(min_length=20)
	camera_id: str = Field(default=settings.default_camera_id, min_length=1, max_length=50)


class AttendanceVerifyResponse(BaseModel):
	student_id: str
	name: str
	similarity_score: float
	threshold: float
	success: bool
	message: str | None = None
