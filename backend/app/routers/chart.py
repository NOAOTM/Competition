import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import get_settings
from ..dependencies import current_user
from ..models import User
from ..services.chart_service import create_chart, read_table

router = APIRouter(prefix="/api/v1/chart", tags=["chart"])


async def _save_upload(file: UploadFile) -> Path:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="仅支持 CSV 和 XLSX 表格；扫描表格请先 OCR 识别")
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="表格文件不能超过 20 MB")
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    source = upload_dir / f"chart-{uuid.uuid4().hex}{extension}"
    source.write_bytes(raw)
    return source


@router.post("/columns")
async def inspect_columns(file: UploadFile = File(...), _: User = Depends(current_user)):
    source = await _save_upload(file)
    try:
        frame = await asyncio.to_thread(read_table, source)
        if frame.empty:
            raise ValueError("文件中没有数据行")
        return {"columns": [str(column) for column in frame.columns], "sample": frame.head(5).fillna("").astype(str).to_dict("records")}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"表格读取失败：{exc}") from exc


@router.post("/render")
async def render_chart(
    file: UploadFile = File(...),
    chart_type: str = Form("line"),
    x_column: str = Form(...),
    y_column: str = Form(...),
    z_column: str = Form(""),
    _: User = Depends(current_user),
):
    source = await _save_upload(file)
    settings = get_settings()
    output_dir = Path(settings.output_dir) / "charts"
    try:
        result = await asyncio.to_thread(
            create_chart, source, output_dir, chart_type, x_column, y_column, z_column or None
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"图表生成失败：{exc}") from exc
    return FileResponse(result, media_type="image/png", filename=result.name)
