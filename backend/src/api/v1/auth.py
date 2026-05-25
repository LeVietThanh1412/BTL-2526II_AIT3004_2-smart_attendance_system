from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if request.username == settings.admin_username and request.password == settings.admin_password:
        payload = {
            "sub": request.username,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        return LoginResponse(token=token)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc mật khẩu không chính xác."
    )

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=403, detail="Not authorized")
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn."
        )
