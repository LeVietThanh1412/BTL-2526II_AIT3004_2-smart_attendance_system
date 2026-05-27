from pydantic import BaseModel, Field

from src.core.config import settings


class AttendanceCheckRequest(BaseModel):
	camera_id: str = Field(default=settings.default_camera_id, min_length=1, max_length=50)


class AttendanceCheckResponse(BaseModel):
	status: str
	student_id: str
	student_name: str | None = Field(default=None, description="Tên sinh viên")
	match_score: float = Field(default=0.0, description="Cosine similarity score")
	threshold: float = Field(default=0.6, description="Match threshold used")
	matched: bool = Field(default=False, description="Whether the face matched")
	reason: str | None = Field(default=None, description="Detailed reason for the result")
	message: str
	action: str | None = Field(default=None, description="check_in hoặc check_out")
	is_late: bool | None = Field(default=None, description="True nếu điểm danh muộn")
	check_in_time: str | None = Field(default=None, description="Giờ check-in")
	check_out_time: str | None = Field(default=None, description="Giờ check-out")
	shift_start: str | None = Field(default=None, description="Giờ bắt đầu ca")
	shift_end: str | None = Field(default=None, description="Giờ kết thúc ca")


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
