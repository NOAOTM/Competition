import asyncio
import base64
import json
import re

import httpx
from fastapi import HTTPException

from ..config import get_settings


async def verify_student_id(image: bytes, content_type: str, student_name: str, school: str) -> dict:
    settings = get_settings()
    provider = settings.llm_provider
    base_url = settings.llm_base_url.rstrip("/")
    encoded = base64.b64encode(image).decode("ascii")
    instruction = (
        "仅根据图像进行学生证/校园卡类别审核。不要推断看不清的文字。返回 JSON 对象，字段为 "
        "is_student_id（布尔）、school_matches（布尔）、name_matches（布尔）、likely_edited（布尔）、reason（字符串）。"
        f"申报姓名：{student_name}；申报学校：{school}。检查是否有明显 Photoshop 拼接/修图痕迹；"
        "无法确认的项目必须为 false，并在 reason 中说明。不要复述证件号码。"
    )
    if provider == "ollama":
        model = settings.vision_model
        url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "stream": False,
            "think": False,
            "format": "json",
            "options": {"num_ctx": settings.ollama_num_ctx},
            "messages": [{"role": "user", "content": instruction, "images": [encoded]}],
        }
        headers = {}
    elif provider == "openai":
        model = settings.openai_model
        if not settings.openai_api_key:
            raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法进行多模态证件审核")
        url = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "stream": False,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": instruction},
                {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{encoded}"}},
            ]}],
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    else:
        raise HTTPException(status_code=503, detail=f"不支持的 LLM_PROVIDER：{provider}")

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.ollama_timeout_seconds)) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 500 and attempt < 2:
                await asyncio.sleep(.5 * (2**attempt))
                continue
            response.raise_for_status()
            body = response.json()
            content = body["message"]["content"] if provider == "ollama" else body["choices"][0]["message"]["content"]
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
            start = content.find("{")
            result = json.loads(content[start:] if start >= 0 else content)
            required = ("is_student_id", "school_matches", "name_matches", "likely_edited", "reason")
            if any(field not in result for field in required):
                raise ValueError("证件审核结果缺少必要字段")
            return result
        except httpx.TimeoutException as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(.5 * (2**attempt))
                continue
            raise HTTPException(status_code=504, detail=f"证件审核模型超时（{model}），未改变认证状态") from exc
        except httpx.ConnectError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(.5 * (2**attempt))
                continue
            raise HTTPException(status_code=503, detail=f"无法连接图像模型 {model}；请确认已拉取模型，未改变认证状态") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500 and attempt < 2:
                await asyncio.sleep(.5 * (2**attempt))
                continue
            raise HTTPException(status_code=502, detail=f"证件审核模型返回 HTTP {exc.response.status_code}；未改变认证状态") from exc
        except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError) as exc:
            if isinstance(exc, httpx.RequestError) and attempt < 2:
                last_error = exc
                await asyncio.sleep(.5 * (2**attempt))
                continue
            raise HTTPException(status_code=502, detail="证件审核结果无效；未改变认证状态") from exc
    raise HTTPException(status_code=502, detail=f"证件审核失败：{last_error!s}")
