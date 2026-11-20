from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas import ToolInput, ToolOutput, ToolRunInput
from ..services import run_tool

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


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
