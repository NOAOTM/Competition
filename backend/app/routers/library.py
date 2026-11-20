import csv
import io
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..dependencies import current_user
from ..models import User

router = APIRouter(prefix="/api/v1/library", tags=["library"])
OPENALEX = "https://api.openalex.org/works"
OPEN_KNOWLEDGE_MAPS = "https://openknowledgemaps.org/"


def _abstract(index: dict | None) -> str:
    if not index:
        return ""
    words = [""] * (max((max(positions) for positions in index.values() if positions), default=-1) + 1)
    for word, positions in index.items():
        for position in positions:
            if 0 <= position < len(words):
                words[position] = word
    return " ".join(words)


async def _search(query: str, limit: int) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "ZhenzhiAgent/1.0"}) as client:
            response = await client.get(OPENALEX, params={
                "search": query,
                "per-page": limit,
                "select": "id,doi,title,publication_year,authorships,abstract_inverted_index",
            })
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="OpenAlex 检索超时，请稍后重试") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接 OpenAlex 文献服务：{exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAlex 返回 HTTP {exc.response.status_code}") from exc
    try:
        works = response.json().get("results", [])
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="OpenAlex 返回格式无效") from exc
    output = []
    for work in works:
        authors = [author.get("author", {}).get("display_name", "") for author in work.get("authorships", [])]
        abstract = _abstract(work.get("abstract_inverted_index"))
        output.append({
            "title": work.get("title") or "标题未提供",
            "year": work.get("publication_year"),
            "doi": work.get("doi"),
            "authors": authors,
            "abstract": abstract,
            "openalex_url": work.get("id"),
        })
    return output


@router.get("/search")
async def search_literature(
    q: str = Query(min_length=2, max_length=300),
    limit: int = Query(default=10, ge=1, le=25),
    _: User = Depends(current_user),
):
    results = await _search(q, limit)
    return {"query": q, "provider": "OpenAlex", "results": results, "knowledge_maps_url": OPEN_KNOWLEDGE_MAPS}


@router.get("/export")
async def export_literature(
    q: str = Query(min_length=2, max_length=300),
    _: User = Depends(current_user),
):
    results = await _search(q, 25)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["title", "year", "doi", "authors", "abstract", "openalex_url"])
    writer.writeheader()
    for result in results:
        writer.writerow({**result, "authors": "; ".join(result["authors"])})
    data = ("\ufeff" + output.getvalue()).encode("utf-8")
    filename = f"literature-{quote(q, safe='')[:60]}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
