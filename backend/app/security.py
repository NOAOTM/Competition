from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=get_settings().access_token_expire_minutes
    )
    return jwt.encode({"sub": subject, "exp": expires}, get_settings().secret_key, algorithm="HS256")


def decode_subject(token: str) -> str | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        subject = payload.get("sub")
        return str(subject) if subject is not None else None
    except JWTError:
        return None
