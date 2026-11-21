from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/llm-health")
async def llm_health():
    settings = get_settings()
    provider = settings.llm_provider
    base_url = settings.llm_base_url.rstrip("/")
    model = settings.llm_model
    result = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "reachable": False,
        "model_available": False,
        "mode": "local" if provider == "ollama" else "openai-compatible",
        "models": [],
        "hint": "",
    }

    if provider == "openai" and not settings.openai_api_key:
        result["hint"] = "未配置 OPENAI_API_KEY；请在本地 .env 填入兼容服务凭据"
        return result
    if provider == "openai" and not settings.openai_model:
        result["hint"] = "未配置 OPENAI_MODEL；请在本地 .env 填写兼容服务的模型名称"
        return result
    if provider not in {"ollama", "openai"}:
        result["hint"] = f"不支持的 LLM_PROVIDER：{provider}"
        return result
    if not base_url:
        result["hint"] = "模型服务 base_url 未配置"
        return result

    endpoint = f"{base_url}/api/tags" if provider == "ollama" else (
        f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"} if provider == "openai" else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
        body = response.json()
        if provider == "ollama":
            models = [item.get("name", "") for item in body.get("models", []) if item.get("name")]
        else:
            models = [item.get("id", "") for item in body.get("data", []) if item.get("id")]
        result["models"] = models
        result["reachable"] = True
        result["model_available"] = any(item == model or item.startswith(f"{model}:") for item in models)
        if not result["model_available"]:
            result["hint"] = f"模型服务已连接，但未发现模型 {model}；运行 model.cmd pull {model}"
        else:
            result["hint"] = "模型服务在线"
        return result
    except httpx.ConnectError as exc:
        message = str(exc).lower()
        if provider == "ollama" and urlsplit(base_url).hostname == "ollama":
            hint = "本地 Ollama 容器未启动；请运行 start.cmd 后重试"
        elif (
            "name or service not known" in message
            or "getaddrinfo failed" in message
            or "nodename nor servname" in message
            or "no address associated with hostname" in message
            or "temporary failure in name resolution" in message
        ):
            hint = "模型服务地址无法解析，请检查 .env 中的 OLLAMA_BASE_URL / OPENAI_BASE_URL"
        elif "refused" in message:
            hint = "本地 Ollama 容器未启动；请运行 start.cmd 后重试"
        else:
            hint = "模型服务连接失败，可能是防火墙或网络策略阻止了容器通信"
        result["hint"] = f"{hint}（{exc}）"
    except httpx.HTTPStatusError as exc:
        result["hint"] = f"模型服务返回 HTTP {exc.response.status_code}，请检查服务地址、鉴权与健康状态"
    except (httpx.TimeoutException, httpx.RequestError):
        result["hint"] = "连接模型服务超时；请检查容器状态和防火墙设置"
    except (ValueError, TypeError):
        result["hint"] = "模型服务返回格式无效"
    return result
