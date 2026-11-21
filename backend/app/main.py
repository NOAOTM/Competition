from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import User
from .routers import account, admin, auth, chart, food, library, research, schedule, system, tools
from .security import hash_password

settings = get_settings()
log_dir = Path(settings.log_dir)
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(log_dir / "backend.log", maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"),
    ],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    additions = {
        "phone": "VARCHAR(20)",
        "quota": "INTEGER NOT NULL DEFAULT 100",
        "auth_status": "VARCHAR(20) NOT NULL DEFAULT '未认证'",
        "quota_expires_at": "DATETIME",
        "is_admin": "BOOLEAN NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
    settings = get_settings()
    if settings.admin_username and settings.admin_password:
        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.username == settings.admin_username).first()
            if admin is None:
                admin = User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    nickname="系统管理员",
                    grade="管理员",
                    major="",
                    is_admin=True,
                )
                db.add(admin)
            else:
                admin.is_admin = True
            db.commit()
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(tools.router)
app.include_router(system.router)
app.include_router(chart.router)
app.include_router(library.router)
app.include_router(food.router)
app.include_router(schedule.router)
app.include_router(admin.router)
app.include_router(research.router)
app.include_router(research.download_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "zhenzhi-agent"}
