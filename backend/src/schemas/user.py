from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemberRegistrationRequest(BaseModel):
	student_id: str = Field(min_length=3, max_length=30)
	name: str = Field(min_length=1, max_length=255)
	class_name: str = Field(default="", max_length=100)
	images_base64: list[str] = Field(min_length=1)


class MemberRegistrationResponse(BaseModel):
	student_id: str
	name: str
	status: str
	task_id: str
	message: str

	model_config = ConfigDict(from_attributes=True)
