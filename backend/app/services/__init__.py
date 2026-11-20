from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import QuotaUsage, ToolRequest, User
from .llm_client import chat

FEATURE_COSTS = {
    "literature-guide": 10,
    "polish": 5,
    "translate": 5,
    "research-design": 10,
    "knowledge-frontier": 10,
    "diagram": 10,
    "data-analysis": 10,
    "literature-search": 10,
    "writing": 5,
    "study-plan": 5,
}

FEATURE_INSTRUCTIONS = {
    "literature-guide": "请依据用户提供的资料进行文献导读，区分原文事实和解释，不得补造引用。",
    "polish": "请进行学术中文润色，保留原意，不虚构事实或引用。",
    "translate": "请准确翻译内容，保留格式和专业术语，只输出译文。",
    "research-design": "请提出可执行的研究问题、方法、数据需求、伦理风险和局限，明确假设。",
    "knowledge-frontier": "请分析相关研究方向并注明知识时效与不确定性；不得声称已联网检索。",
    "diagram": "请将信息整理为 Mermaid 流程图代码，并在代码块前简要说明结构。",
    "data-analysis": "请依据用户提供的数据或描述分析，说明方法和限制。未提供数据时不得编造统计结论。",
    "literature-search": "请生成数据库可用的学术检索式、关键词及筛选策略；不得编造论文或 DOI。",
    "writing": "请组织学术写作提纲，只使用用户提供的信息，不得补造引用或事实。",
    "study-plan": "请依据用户给出的目标和时间安排可执行的计划，标注需要确认的假设。",
}


def consume_quota(db: Session, user: User, feature: str) -> int:
    cost = FEATURE_COSTS.get(feature)
    if cost is None:
        raise HTTPException(status_code=400, detail="不支持此功能")
    if user.balance < cost:
        raise HTTPException(status_code=402, detail="额度不足，请签到或完成认证后再试")
    user.balance -= cost
    user.quota = max(0, user.quota - cost)
    db.add(QuotaUsage(user_id=user.id, feature=feature, cost=cost))
    return cost


async def run_tool(
    db: Session,
    user: User,
    feature: str,
    text: str,
    target_language: str = "中文",
    model: str | None = None,
    analysis_mode: str = "standard",
) -> tuple[str, int]:
    instruction = FEATURE_INSTRUCTIONS.get(feature)
    if instruction is None:
        raise HTTPException(status_code=400, detail="不支持此功能")
    if feature == "translate":
        instruction = f"{instruction} 目标语言：{target_language}。"
    if analysis_mode == "careful":
        instruction += " 请额外核对逻辑衔接与遗漏，但只输出结论，不输出隐藏推理过程。"
    result = await chat(
        [{"role": "system", "content": instruction}, {"role": "user", "content": text}],
        model=model,
    )
    cost = consume_quota(db, user, feature)
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
    user.quota += 10
    db.commit()
    return True
