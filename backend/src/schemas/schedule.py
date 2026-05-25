from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class ScheduleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=5, description="0: Monday, 5: Saturday")
    shifts: str = Field(..., description="Comma separated shifts, e.g. '1,2,3'")

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
    id: int
    user_id: int
    is_approved: bool
    is_active: bool
    created_at: datetime | None = None
    approved_at: datetime | None = None

    class Config:
        from_attributes = True

class ScheduleHistoryResponse(BaseModel):
    created_at: datetime
    approved_at: datetime | None
    is_approved: bool
    schedules: List[ScheduleBase]

class ScheduleListUpdate(BaseModel):
    schedules: List[ScheduleBase]
