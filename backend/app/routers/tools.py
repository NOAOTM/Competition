from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas import ToolInput, ToolOutput
from ..services import run_tool

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def execute(feature: str, payload: ToolInput, db: Session, user: User) -> ToolOutput:
    result, cost = run_tool(db, user, feature, payload.text, payload.target_language)
    return ToolOutput(feature=feature, result=result, cost=cost, balance=user.balance)


@router.post("/literature-guide", response_model=ToolOutput)
def literature(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return execute("literature-guide", payload, db, user)


@router.post("/polish", response_model=ToolOutput)
def polish(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return execute("polish", payload, db, user)


@router.post("/translate", response_model=ToolOutput)
def translate(payload: ToolInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return execute("translate", payload, db, user)
