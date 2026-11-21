import json
import re
from collections.abc import Callable
from pathlib import Path

from .llm_client import chat
from .pdf_parser import split_chunks

PROMPT_VERSION = "v20-pass-2"
REQUIRED_KEYS = ("meta", "one_sentence_summary", "core_concepts", "logic_nodes", "logic_edges", "formulas", "uncertainties")


def parse_json_response(text: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise
        result, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    if not isinstance(result, dict):
        raise ValueError("模型结果不是 JSON 对象")
    for key in REQUIRED_KEYS:
        if key not in result:
            result[key] = [] if key in {"core_concepts", "logic_nodes", "logic_edges", "formulas", "uncertainties"} else ""
    for key in ("core_concepts", "logic_nodes", "logic_edges", "formulas", "uncertainties"):
        if not isinstance(result[key], list):
            result[key] = [result[key]] if result[key] else []
    return result


async def analyze_document(
    text: str,
    metadata: dict[str, object],
    question: str,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
    progress: Callable[[int, str, str], None],
    model: str | None = None,
    raw_dir: Path | None = None,
) -> tuple[dict, list[str]]:
    chunks, truncated = split_chunks(text, chunk_size, overlap, max_chunks)
    if not chunks:
        raise ValueError("未能从文档中提取可分析的文本")
    warnings = ["文档较长，已按内容重要性选取部分片段分析。"] if truncated else []
    progress(8, "Pass 0 · 元数据识别", "正在识别标题、研究领域和核心主题")
    meta = await chat([
        {"role": "system", "content": "从文献内容提取可确认的标题、作者、年份和研究领域；无从确认的字段填“原文未说明”。只返回 JSON 对象。"},
        {"role": "user", "content": text[: min(len(text), 12000)]},
    ], json_mode=True, model=model)
    try:
        parsed_meta = json.loads(meta)
    except json.JSONDecodeError:
        if raw_dir:
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "raw_response_pass0.txt").write_text(meta, encoding="utf-8")
        parsed_meta = {"title": metadata.get("filename", ""), "author": "原文未说明", "year": "原文未说明", "field": "原文未说明"}

    chunk_results = []
    for index, chunk in enumerate(chunks):
        progress(12 + int(55 * index / max(1, len(chunks))), f"Pass 1 · 文献分块 {index + 1}/{len(chunks)}", "正在结构化提取证据、方法、结果与公式")
        response = await chat([
            {"role": "system", "content": "根据提供的文献片段，用中文返回 JSON：core_concepts、logic_nodes、logic_edges、formulas、uncertainties。只摘录本片段支持的信息；公式不可编造，缺失处写“原文未说明”。"},
            {"role": "user", "content": f"用户关注：{question}\n片段 {index + 1}/{len(chunks)}:\n{chunk}"},
        ], json_mode=True, model=model)
        try:
            chunk_results.append(parse_json_response(response))
        except (json.JSONDecodeError, ValueError):
            if raw_dir:
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"raw_response_chunk_{index + 1}.txt").write_text(response, encoding="utf-8")
            warnings.append(f"第 {index + 1} 个文本片段未能解析为结构化结果。")

    progress(70, "Pass 2 · 综合逻辑链", "正在合并片段，生成结论、证据链和不确定项")
    response = await chat([
        {"role": "system", "content": "你是科研文献导读助手。仅使用输入信息，返回严格 JSON 对象，字段必须为 meta、one_sentence_summary、core_concepts[]、logic_nodes[]、logic_edges[]、formulas[]、uncertainties[]。按背景→问题→方法→结果→结论→局限组织。对公式解释符号、单位、适用条件（原文没有就写“原文未说明”），不得捏造结论或引用。"},
        {"role": "user", "content": f"原文元数据：{json.dumps(parsed_meta, ensure_ascii=False)}\n用户关注：{question}\n分块分析：{json.dumps(chunk_results, ensure_ascii=False)}"},
    ], json_mode=True, model=model)
    try:
        result = parse_json_response(response)
    except (json.JSONDecodeError, ValueError):
        if raw_dir:
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "raw_response_pass2.txt").write_text(response, encoding="utf-8")
        raise
    if not result.get("meta"):
        result["meta"] = parsed_meta
    if truncated:
        result["uncertainties"].append("文档超出默认分块上限，结果仅覆盖所选重要片段。")
    progress(78, "质量门禁", "检查结果结构、公式说明和不确定项")
    if len(result["core_concepts"]) == 0:
        warnings.append("模型未提取到核心概念，请人工核验原文。")
    progress(82, "产物生成", "正在生成知识报告、逻辑图和组会演示稿")
    return result, warnings
