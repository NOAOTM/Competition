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
    balance: int
    verification_status: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ToolInput(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    target_language: str = "中文"


class ToolOutput(BaseModel):
    feature: str
    result: str
    cost: int
    balance: int


class VerificationOut(BaseModel):
    status: str
    image_path: str
