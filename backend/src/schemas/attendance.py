from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceVerifyRequest(BaseModel):
	image_base64: str = Field(min_length=20)


class AttendanceVerifyResponse(BaseModel):
	status: str
	task_id: str
	message: str
