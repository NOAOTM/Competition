from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas import AdminUserUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要独立管理员账户")


@router.get("/users")
def list_users(
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(current_user),
):
    _require_admin(admin)
    limit = min(max(limit, 1), 200)
    users = db.scalars(select(User).order_by(User.id).offset(max(offset, 0)).limit(limit)).all()
    return [{
        "id": user.id,
        "username": user.username,
        "phone": user.phone,
        "nickname": user.nickname,
        "grade": user.grade,
        "major": user.major,
        "balance": user.balance,
        "quota": user.quota,
        "auth_status": user.auth_status,
        "is_active": user.is_active,
        "created_at": user.created_at,
    } for user in users]


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(current_user),
):
    _require_admin(admin)
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    values = payload.model_dump(exclude_unset=True)
    if user.id == admin.id and values.get("is_active") is False:
        raise HTTPException(status_code=400, detail="管理员不能停用自己的账户")
    if "is_active" in values:
        user.is_active = values["is_active"]
    if "balance" in values:
        user.balance = values["balance"]
        user.quota = values["balance"]
    if "auth_status" in values:
        user.auth_status = values["auth_status"]
        user.verification_status = values["auth_status"]
    db.commit()
    return {"id": user.id, "is_active": user.is_active, "balance": user.balance, "auth_status": user.auth_status}
