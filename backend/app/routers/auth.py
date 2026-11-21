from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import Token, UserLogin
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=410)
def legacy_register():
    raise HTTPException(status_code=410, detail="注册需要手机号、算术验证码和短信验证码，请使用 /api/v1/account/register")


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(or_(User.username == payload.username, User.phone == payload.username)))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return Token(access_token=create_access_token(str(user.id)))
