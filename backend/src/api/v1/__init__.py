from fastapi import APIRouter

from src.api.v1.attendance import router as attendance_router
from src.api.v1.members import router as members_router


api_v1_router = APIRouter()
api_v1_router.include_router(members_router)
api_v1_router.include_router(attendance_router)
