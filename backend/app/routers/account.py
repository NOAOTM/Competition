import re
import secrets
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from random import SystemRandom

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..dependencies import current_user
from ..models import User, VerificationRequest
from ..schemas import PhoneRegistration, SmsCodeRequest, UserOut, VerificationOut
from ..security import hash_password
from ..services import check_in
from ..services.vision_client import verify_student_id

router = APIRouter(prefix="/api/v1/account", tags=["account"])
_captchas: dict[str, tuple[int, float]] = {}
_sms_codes: dict[str, tuple[str, float]] = {}


def _valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"1[3-9]\d{9}", phone))


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
    student_name: str = Form(..., min_length=1, max_length=100),
    school: str = Form(..., min_length=1, max_length=150),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="只支持 PNG 或 JPEG 图片")
    image = await file.read(10 * 1024 * 1024 + 1)
    if len(image) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="学生证图片不能超过 10 MB")
    assessment = await verify_student_id(image, file.content_type, student_name, school)
    approved = (
        assessment.get("is_student_id") is True
        and assessment.get("school_matches") is True
        and assessment.get("name_matches") is True
        and assessment.get("likely_edited") is False
    )
    target_dir = Path(get_settings().upload_dir) / "verifications"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{user.id}_{uuid.uuid4().hex}{Path(file.filename or 'student-card.jpg').suffix.lower()}"
    target.write_bytes(image)
    user.verification_status = "已认证" if approved else "未通过"
    user.auth_status = user.verification_status
    user.verification_image_path = str(target)
    if approved:
        years = 3 if any(term in user.grade for term in ("研究生", "硕士", "博士")) else 4
        user.quota = years * 100
        user.balance = user.quota
        user.quota_expires_at = datetime.utcnow() + timedelta(days=years * 365)
    reason = str(assessment.get("reason", "请人工核验模型审核结果"))
    db.add(VerificationRequest(user_id=user.id, image_path=str(target), status=user.verification_status))
    db.commit()
    return VerificationOut(status=user.verification_status, image_path=str(target), reason=reason, quota=user.quota)


@router.get("/captcha")
def create_captcha():
    first = SystemRandom().randint(1, 20)
    second = SystemRandom().randint(1, 20)
    challenge_id = secrets.token_urlsafe(18)
    _captchas[challenge_id] = (first + second, time.monotonic() + 300)
    return {"captcha_id": challenge_id, "question": f"{first} + {second} = ?"}


@router.post("/sms-code")
def send_demo_sms(payload: SmsCodeRequest):
    if not _valid_phone(payload.phone):
        raise HTTPException(status_code=422, detail="请输入有效的 11 位手机号")
    challenge = _captchas.pop(payload.captcha_id, None)
    if not challenge or challenge[1] < time.monotonic() or str(challenge[0]) != payload.captcha_answer.strip():
        raise HTTPException(status_code=400, detail="算术验证码错误或已过期")
    if get_settings().app_env != "development":
        raise HTTPException(status_code=503, detail="未配置短信服务商，生产环境不发送演示验证码")
    code = f"{SystemRandom().randint(0, 999999):06d}"
    _sms_codes[payload.phone] = (code, time.monotonic() + 300)
    print(f"[演示短信] {payload.phone} 验证码：{code}", flush=True)
    return {"delivery": "demo", "message": "演示短信验证码（5 分钟有效）", "code": code}


@router.post("/register")
def register_phone(payload: PhoneRegistration, db: Session = Depends(get_db)):
    sms = _sms_codes.get(payload.phone)
    if not sms or sms[1] < time.monotonic() or not secrets.compare_digest(sms[0], payload.sms_code):
        raise HTTPException(status_code=400, detail="短信验证码错误或已过期")
    if db.query(User).filter((User.phone == payload.phone) | (User.username == payload.phone)).first():
        raise HTTPException(status_code=409, detail="手机号已注册")
    user = User(
        username=payload.phone,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        grade=payload.grade,
        major=payload.major,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _sms_codes.pop(payload.phone, None)
    return UserOut.model_validate(user)
