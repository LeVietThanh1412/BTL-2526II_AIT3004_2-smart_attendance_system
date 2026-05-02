from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AttendanceVerifyRequest(BaseModel):
    image_base64: str = Field(min_length=20)


class AttendanceVerifyResponse(BaseModel):
    status: str
    task_id: str
    message: str


class AttendanceResultResponse(BaseModel):
    task_id: str
    status: str           # "processing" | "success" | "failed"
    student_id: str | None = None
    name: str | None = None
    similarity: float | None = None
    message: str | None = None
    timestamp: datetime | None = None
