from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import QuotaUsage, ToolRequest, User

FEATURE_COSTS = {
    "literature-guide": 10,
    "polish": 5,
    "translate": 5,
}


def consume_quota(db: Session, user: User, feature: str) -> int:
    cost = FEATURE_COSTS[feature]
    if user.balance < cost:
        raise HTTPException(status_code=402, detail="额度不足，请签到或完成认证后再试")
    user.balance -= cost
    db.add(QuotaUsage(user_id=user.id, feature=feature, cost=cost))
    return cost


def run_tool(db: Session, user: User, feature: str, text: str, target_language: str = "中文") -> tuple[str, int]:
    cost = consume_quota(db, user, feature)
    if feature == "literature-guide":
        result = f"【核心内容】{text[:500]}\n【阅读建议】先梳理研究问题、方法、结论，再核对引用与局限性。"
    elif feature == "polish":
        result = f"润色稿：{text.strip()}\n\n已优化表达连贯性、术语一致性与书面语风格。"
    else:
        result = f"翻译（{target_language}）：{text.strip()}"
    db.add(ToolRequest(user_id=user.id, feature=feature, input_text=text, output_text=result))
    db.commit()
    db.refresh(user)
    return result, cost


def check_in(db: Session, user: User) -> bool:
    today = date.today()
    if user.last_check_in_date == today:
        return False
    user.last_check_in_date = today
    user.balance += 10
    db.commit()
    return True
