from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceVerifyRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	image_base64: str = Field(min_length=20)


class AttendanceVerifyResponse(BaseModel):
	student_id: str
	name: str
	similarity_score: float
	threshold: float
	success: bool
	timestamp: datetime
