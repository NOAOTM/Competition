from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=50)
    major: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    grade: str
    major: str
    phone: str | None = None
    balance: int
    quota: int
    verification_status: str
    auth_status: str
    is_admin: bool = False
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ToolInput(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    target_language: str = "中文"


class ToolRunInput(ToolInput):
    feature: str = Field(min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=120)
    analysis_mode: str = Field(default="standard", pattern="^(standard|careful)$")


class ToolOutput(BaseModel):
    feature: str
    result: str
    cost: int
    balance: int


class VerificationOut(BaseModel):
    status: str
    image_path: str
    reason: str = ""
    quota: int = 0


class PhoneRegistration(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=50)
    major: str = Field(min_length=1, max_length=100)


class SmsCodeRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    captcha_id: str = Field(min_length=8, max_length=80)
    captcha_answer: str = Field(min_length=1, max_length=8)


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    details: str = Field(default="", max_length=2000)


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    balance: int | None = Field(default=None, ge=0, le=1_000_000)
    auth_status: str | None = Field(default=None, max_length=20)
