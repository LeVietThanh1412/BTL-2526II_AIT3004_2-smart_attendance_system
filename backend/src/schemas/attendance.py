from pydantic import BaseModel, Field


class AttendanceCheckRequest(BaseModel):
	camera_id: str = Field(default="cam_01", min_length=1, max_length=50)


class AttendanceCheckResponse(BaseModel):
	status: str
	student_id: str
	message: str


class AttendanceVerifyRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	image_base64: str = Field(min_length=20)
	camera_id: str = Field(default="cam_01", min_length=1, max_length=50)


class AttendanceVerifyResponse(BaseModel):
	student_id: str
	name: str
	similarity_score: float
	threshold: float
	success: bool
	message: str | None = None
