import asyncio
import hashlib
import json
import re
import time

import httpx
from fastapi import HTTPException

from ..config import get_settings

_cache: dict[str, tuple[float, str]] = {}
_CACHE_SECONDS = 3600


def _clean_response(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def _cache_key(messages: list[dict[str, str]], json_mode: bool, model: str) -> str:
    settings = get_settings()
    value = json.dumps(
        [settings.llm_provider, settings.llm_base_url, model, settings.ollama_num_ctx, json_mode, messages],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def chat(messages: list[dict[str, str]], *, json_mode: bool = False, model: str | None = None) -> str:
    settings = get_settings()
    provider = settings.llm_provider
    base_url = settings.llm_base_url.rstrip("/")
    selected_model = model or settings.llm_model
    if provider not in {"ollama", "openai"}:
        raise HTTPException(status_code=503, detail=f"不支持的 LLM_PROVIDER：{provider}")
    if not base_url:
        raise HTTPException(status_code=503, detail="未配置模型服务地址")
    if provider == "openai" and not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="已选择 OpenAI 兼容服务，但未在 .env 配置 OPENAI_API_KEY")
    if not selected_model:
        raise HTTPException(status_code=503, detail="已选择 OpenAI 兼容服务，但未在 .env 配置 OPENAI_MODEL")

    key = _cache_key(messages, json_mode, selected_model)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_SECONDS:
        return cached[1]
    _cache.pop(key, None)

    if provider == "ollama":
        url = f"{base_url}/api/chat"
        payload = {
            "model": selected_model,
            "stream": False,
            "think": False,
            "options": {"num_ctx": settings.ollama_num_ctx},
            "messages": messages,
        }
        if json_mode:
            payload["format"] = "json"
        headers = {}
    else:
        url = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"
        payload = {
            "model": selected_model,
            "stream": False,
            "messages": messages,
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.ollama_timeout_seconds)) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 500 and attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            response.raise_for_status()
            body = response.json()
            if provider == "ollama":
                content = body["message"]["content"]
            else:
                content = body["choices"][0]["message"]["content"]
            result = _clean_response(content)
            if not result:
                raise HTTPException(status_code=502, detail="模型未返回可用内容；未扣除额度")
            _cache[key] = (time.monotonic(), result)
            return result
        except httpx.TimeoutException as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            raise HTTPException(status_code=504, detail="模型生成超时，请缩短输入或稍后重试；未扣除额度") from exc
        except httpx.ConnectError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            raise HTTPException(status_code=503, detail=f"无法连接模型服务（{base_url}），请检查服务地址和容器状态；未扣除额度") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500 and attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            raise HTTPException(
                status_code=502,
                detail=f"模型服务返回错误（HTTP {exc.response.status_code}），请确认模型已拉取；未扣除额度",
            ) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="模型服务返回格式无效；未扣除额度") from exc
        except httpx.RequestError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            raise HTTPException(status_code=502, detail="请求模型服务失败；未扣除额度") from exc
    raise HTTPException(status_code=502, detail=f"模型服务请求失败：{last_error!s}")
