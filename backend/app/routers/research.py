import asyncio
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..dependencies import current_user
from ..models import ToolRequest, User
from ..services import consume_quota
from ..services.ai_agent import PROMPT_VERSION, analyze_document
from ..services.file_generator import generate_research_files
from ..services.llm_client import chat
from ..services.pdf_parser import extract_document_text

router = APIRouter(prefix="/api/v1/agent", tags=["research"])
download_router = APIRouter(prefix="/api/v1", tags=["downloads"])
_tasks: dict[str, dict] = {}
_workers: set[asyncio.Task] = set()
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _update(task_id: str, progress: int, stage: str, message: str) -> None:
    task = _tasks.get(task_id)
    if task:
        task.update(status="running", progress=progress, stage=stage, message=message)


async def _run_task(task_id: str, user_id: int, upload_path: Path, question: str, model: str) -> None:
    settings = get_settings()
    task = _tasks[task_id]
    output_root = Path(settings.output_dir)
    output_dir = output_root / task_id
    cache_dir = output_root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        task.update(status="running", progress=3, stage="文档解析", message="正在读取文档文字与页面结构")
        text, metadata = await asyncio.to_thread(extract_document_text, upload_path)
        if len(text) < 80:
            raise ValueError("未能提取足够的正文文本；扫描 PDF 请确认容器已安装 Tesseract 中文语言包")

        sha = hashlib.sha256(upload_path.read_bytes()).hexdigest()
        cache_key = hashlib.sha256(
            f"{sha}|{settings.chunk_size}|{settings.chunk_overlap}|{settings.max_chunks}|{settings.llm_model}|"
            f"{settings.ollama_num_ctx}|{settings.pipeline_passes}|{settings.llm_provider}|{settings.llm_base_url}|"
            f"{model}|{question}|{PROMPT_VERSION}".encode()
        ).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"
        warnings: list[str]
        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            source_dir = Path(cached["output_dir"])
            try:
                source_dir.resolve().relative_to(output_root.resolve())
                cache_files = [
                    name for name in cached["files"]
                    if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9._-]+", name)
                ]
            except (ValueError, KeyError, TypeError):
                cache_files = []
            if source_dir.is_dir() and cache_files:
                task.update(status="running", progress=76, stage="命中缓存", message="文档、模型和提示版本匹配，跳过模型推理")
                output_dir.mkdir(parents=True, exist_ok=True)
                files = []
                for name in cache_files:
                    source = source_dir / name
                    if source.exists():
                        shutil.copy2(source, output_dir / name)
                        files.append(name)
                knowledge = cached["knowledge"]
                warnings = cached["warnings"]
            else:
                cached = None
        else:
            cached = None
        if not cached:
            def progress(percent: int, stage: str, message: str) -> None:
                _update(task_id, percent, stage, message)

            knowledge, warnings = await analyze_document(
                text, metadata, question, settings.chunk_size, settings.chunk_overlap,
                settings.max_chunks, progress, model, output_dir,
            )
            files = await asyncio.to_thread(generate_research_files, knowledge, output_dir, upload_path.name, warnings)
            files.extend(path.name for path in output_dir.glob("raw_response_*.txt"))
            cache_file.write_text(json.dumps({
                "output_dir": str(output_dir),
                "files": files,
                "knowledge": knowledge,
                "warnings": warnings,
            }, ensure_ascii=False), encoding="utf-8")

        is_english = len(re.findall(r"[A-Za-z]", text)) > len(re.findall(r"[\u4e00-\u9fff]", text)) * 2
        if is_english and not (output_dir / "translation.md").exists():
            task.update(status="running", progress=88, stage="双语对照", message="英文原文检测到，正在生成节选对照翻译")
            try:
                translated = await chat([
                    {"role": "system", "content": "将用户提供的英文文献片段翻译为中文，保留术语和段落；注明这是自动翻译节选。"},
                    {"role": "user", "content": text[:12000]},
                ])
                (output_dir / "translation.md").write_text(
                    "# 英文文献对照翻译（节选）\n\n"
                    "以下内容为自动翻译，不替代原文核对。\n\n"
                    "## 原文节选\n\n" + text[:12000] + "\n\n## 中文翻译\n\n" + translated + "\n",
                    encoding="utf-8",
                )
                files.append("translation.md")
            except Exception as exc:
                warnings.append(f"英文对照翻译未完成：{exc}")

        if warnings:
            (output_dir / "run.log").write_text("质量门禁：仅提供警告，不阻断结果生成。\n" + "\n".join(warnings), encoding="utf-8")
        cache_file.write_text(json.dumps({
            "output_dir": str(output_dir),
            "files": files,
            "knowledge": knowledge,
            "warnings": warnings,
        }, ensure_ascii=False), encoding="utf-8")
        file_ids = []
        for name in files:
            file_id = f"{task_id}--{name}"
            file_ids.append({"label": name, "url": f"/api/v1/download/{file_id}"})
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise ValueError("账户不存在，无法保存本次任务")
            cost = consume_quota(db, user, "literature-guide")
            db.add(ToolRequest(
                user_id=user.id,
                feature="literature-guide",
                input_text=f"{upload_path.name}\n{question}",
                output_text=str(knowledge.get("one_sentence_summary", "")),
            ))
            db.commit()
        finally:
            db.close()
        summary = str(knowledge.get("one_sentence_summary", "原文未说明"))
        task.update(
            status="done", progress=100, stage="完成",
            message=f"文献导读已完成，消耗 {cost} 额度。",
            result={"summary": summary, "downloads": file_ids, "warnings": warnings},
        )
    except Exception as exc:
        task.update(status="error", stage="处理失败", message="本次未完成，不会扣除额度。", error=str(exc))


@router.post("/research", status_code=202)
async def start_research(
    file: UploadFile = File(...),
    question: str = Form("请导读这篇文献"),
    model: str = Form(""),
    analysis_mode: str = Form("standard"),
    user: User = Depends(current_user),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF、DOCX 和 TXT 文件")
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="上传文件不能超过 50 MB")
    selected_model = model.strip() or get_settings().llm_model
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,120}", selected_model):
        raise HTTPException(status_code=422, detail="模型名称格式无效")
    if analysis_mode not in {"standard", "careful"}:
        raise HTTPException(status_code=422, detail="分析模式无效")
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    task_id = str(uuid.uuid4())
    upload_path = upload_dir / f"{task_id}{extension}"
    upload_path.write_bytes(raw)
    _tasks[task_id] = {
        "user_id": user.id, "status": "queued", "progress": 0,
        "stage": "排队中", "message": "任务已创建，等待处理",
    }
    selected_question = question.strip() or "请导读这篇文献"
    if analysis_mode == "careful":
        selected_question += "；请额外核对逻辑衔接与遗漏。"
    worker = asyncio.create_task(_run_task(task_id, user.id, upload_path, selected_question, selected_model))
    _workers.add(worker)
    worker.add_done_callback(_workers.discard)
    return {"task_id": task_id, "status": "queued", "progress_url": f"/api/v1/agent/progress/{task_id}"}


@router.get("/progress/{task_id}")
def research_progress(task_id: str, user: User = Depends(current_user)):
    task = _tasks.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {key: value for key, value in task.items() if key != "user_id"}


@download_router.get("/download/{file_id}")
def download_research_file(file_id: str, user: User = Depends(current_user)):
    if not re.fullmatch(r"[a-f0-9-]{36}--[A-Za-z0-9._-]+", file_id):
        raise HTTPException(status_code=400, detail="文件编号无效")
    task_id, name = file_id.split("--", 1)
    task = _tasks.get(task_id)
    if not task or task["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="文件不存在")
    path = Path(get_settings().output_dir) / task_id / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件尚未生成或已不存在")
    return FileResponse(path, filename=name)
