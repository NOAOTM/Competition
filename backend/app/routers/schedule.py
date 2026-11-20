import re
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..dependencies import current_user
from ..models import CalendarEntry, User
from ..schemas import ReminderCreate

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


@router.get("/items")
def list_items(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(
        select(CalendarEntry)
        .where(CalendarEntry.user_id == user.id)
        .order_by(CalendarEntry.starts_at)
    ).all()
    return [{
        "id": item.id,
        "title": item.title,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "kind": item.kind,
        "details": item.details,
        "source": item.source,
    } for item in items]


@router.post("/reminders", status_code=201)
def create_reminder(payload: ReminderCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = CalendarEntry(
        user_id=user.id,
        title=payload.title,
        starts_at=payload.starts_at.replace(tzinfo=None),
        kind="reminder",
        details=payload.details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "title": entry.title, "starts_at": entry.starts_at, "kind": entry.kind}


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = db.scalar(select(CalendarEntry).where(CalendarEntry.id == item_id, CalendarEntry.user_id == user.id))
    if not entry:
        raise HTTPException(status_code=404, detail="日程不存在")
    db.delete(entry)
    db.commit()


@router.post("/import")
async def import_schedule(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="课表导入支持 CSV 和 XLSX")
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="课表文件不能超过 10 MB")
    tmp = Path(get_settings().upload_dir) / f"schedule-import{extension}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(content)
    try:
        frame = pd.read_csv(tmp, encoding="utf-8-sig") if extension == ".csv" else pd.read_excel(tmp)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"课表读取失败：{exc}") from exc
    aliases = {
        "title": ("title", "课程", "课程名称", "course"),
        "date": ("date", "日期", "上课日期"),
        "start": ("start", "开始时间", "上课时间"),
        "end": ("end", "结束时间", "下课时间"),
        "location": ("location", "地点", "教室"),
    }
    columns = {str(column).strip().lower(): column for column in frame.columns}

    def find_column(key: str):
        return next((columns[name.lower()] for name in aliases[key] if name.lower() in columns), None)

    title_col, date_col = find_column("title"), find_column("date")
    start_col, end_col, location_col = find_column("start"), find_column("end"), find_column("location")
    if not title_col or not date_col or not start_col:
        raise HTTPException(status_code=422, detail="课表至少需要“课程、日期、开始时间”列；可选“结束时间、地点”")
    created = []
    for _, row in frame.head(500).iterrows():
        try:
            starts = pd.to_datetime(f"{row[date_col]} {row[start_col]}").to_pydatetime()
            ends = pd.to_datetime(f"{row[date_col]} {row[end_col]}").to_pydatetime() if end_col and pd.notna(row[end_col]) else None
        except (ValueError, TypeError):
            continue
        title = str(row[title_col]).strip()
        if not title or title.lower() == "nan":
            continue
        location = str(row[location_col]).strip() if location_col and pd.notna(row[location_col]) else ""
        created.append(CalendarEntry(
            user_id=user.id,
            title=title[:200],
            starts_at=starts,
            ends_at=ends,
            kind="class",
            details=location[:1000],
            source="import",
        ))
    if not created:
        raise HTTPException(status_code=422, detail="没有识别到有效课表行，请检查日期与时间格式")
    db.add_all(created)
    db.commit()
    return {"imported": len(created), "message": f"已导入 {len(created)} 条课程日程"}


@router.post("/chaoxing/sync")
async def sync_chaoxing(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cookie = get_settings().chaoxing_cookie
    if not cookie:
        raise HTTPException(
            status_code=503,
            detail="学习通作业同步需要已登录账号的 CHAOXING_COOKIE；请配置到本机 .env，不要提交凭据。登录入口：i.mooc.chaoxing.com",
        )
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"Cookie": cookie}) as client:
            response = await client.get("https://i.mooc.chaoxing.com/")
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="学习通连接超时") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接学习通：{exc}") from exc
    html = response.text
    if "login" in str(response.url).lower() or "登录" in html[:5000]:
        raise HTTPException(status_code=401, detail="学习通会话无效或已过期，请更新本地 CHAOXING_COOKIE")
    deadlines = re.findall(r"(?:截止时间|截止日期|deadline)[^0-9]{0,24}(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2})?)", html, re.IGNORECASE)
    if not deadlines:
        raise HTTPException(status_code=422, detail="已连接学习通，但首页未返回可识别的作业截止日期；请在课程作业页核对后手动添加提醒")
    return {"connected": True, "deadlines_found": len(deadlines), "deadlines": deadlines, "message": "请逐项核对课程作业后再添加到日历，未自动创建未经确认的提醒"}
