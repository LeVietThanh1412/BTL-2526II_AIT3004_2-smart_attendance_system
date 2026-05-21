from pydantic import BaseModel, Field

from src.core.config import settings


class AttendanceCheckRequest(BaseModel):
	camera_id: str = Field(default=settings.default_camera_id, min_length=1, max_length=50)


class AttendanceCheckResponse(BaseModel):
	status: str
	student_id: str
	match_score: float = Field(default=0.0, description="Cosine similarity score")
	threshold: float = Field(default=0.6, description="Match threshold used")
	matched: bool = Field(default=False, description="Whether the face matched")
	reason: str | None = Field(default=None, description="Detailed reason for the result")
	message: str


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
