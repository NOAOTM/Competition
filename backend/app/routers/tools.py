import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..dependencies import current_user
from ..models import User
from ..schemas import ToolInput, ToolOutput, ToolRunInput
from ..services import run_tool

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])
logger = logging.getLogger(__name__)
_tasks: dict[str, dict] = {}
_workers: set[asyncio.Task] = set()


async def execute(
    feature: str,
    payload: ToolInput,
    db: Session,
    user: User,
    model: str | None = None,
    analysis_mode: str = "standard",
) -> ToolOutput:
    result, cost = await run_tool(db, user, feature, payload.text, payload.target_language, model, analysis_mode)
    return ToolOutput(feature=feature, result=result, cost=cost, balance=user.balance)


async def _run_background_tool(
    task_id: str,
    user_id: int,
    feature: str,
    text: str,
    target_language: str,
    model: str | None,
    analysis_mode: str,
) -> None:
    task = _tasks[task_id]
    task.update(status="running", progress=5, stage="模型推理", message="正在等待真实模型响应")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="账户不存在或已停用")
        result, cost = await run_tool(db, user, feature, text, target_language, model, analysis_mode)
        task.update(
            status="done",
            progress=100,
            stage="完成",
            message=f"模型已返回结果，消耗 {cost} 额度。",
            result={"summary": result, "cost": cost, "balance": user.balance},
        )
    except HTTPException as exc:
        task.update(status="error", stage="任务失败", message="本次未完成，不会扣除额度。", error=str(exc.detail))
    except Exception as exc:
        logger.exception("Background tool task %s failed", task_id)
        task.update(status="error", stage="任务失败", message="本次未完成，不会扣除额度。", error=str(exc))
    finally:
        db.close()


@router.post("/literature-guide", response_model=ToolOutput)
async def literature(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await execute("literature-guide", payload, db, user)


@router.post("/polish", response_model=ToolOutput)
async def polish(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await execute("polish", payload, db, user)


@router.post("/translate", response_model=ToolOutput)
async def translate(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await execute("translate", payload, db, user)


@router.post("/run", response_model=ToolOutput)
async def run(payload: ToolRunInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await execute(payload.feature, payload, db, user, payload.model, payload.analysis_mode)


@router.post("/tasks", status_code=202)
async def start_background_tool(payload: ToolRunInput, user: User = Depends(current_user)):
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "user_id": user.id,
        "status": "queued",
        "progress": 0,
        "stage": "排队中",
        "message": "任务已创建，等待处理",
    }
    worker = asyncio.create_task(_run_background_tool(
        task_id,
        user.id,
        payload.feature,
        payload.text,
        payload.target_language,
        payload.model,
        payload.analysis_mode,
    ))
    _workers.add(worker)
    worker.add_done_callback(_workers.discard)
    return {"task_id": task_id, "status": "queued"}


@router.get("/tasks/{task_id}")
def background_tool_progress(task_id: str, user: User = Depends(current_user)):
    task = _tasks.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {key: value for key, value in task.items() if key != "user_id"}
