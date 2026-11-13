from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import current_user
from ..models import User, VerificationRequest
from ..schemas import UserOut, VerificationOut
from ..services import check_in

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/check-in", response_model=UserOut)
def daily_check_in(db: Session = Depends(get_db), user: User = Depends(current_user)):
    check_in(db, user)
    return user


@router.post("/verification", response_model=VerificationOut, status_code=201)
async def verification(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="只支持 PNG 或 JPEG 图片")
    target_dir = Path("data/verifications")
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "student-card.jpg").name
    target = target_dir / f"{user.id}_{safe_name}"
    target.write_bytes(await file.read())
    user.verification_status = "审核中"
    user.verification_image_path = str(target)
    db.add(VerificationRequest(user_id=user.id, image_path=str(target)))
    db.commit()
    return VerificationOut(status=user.verification_status, image_path=str(target))
