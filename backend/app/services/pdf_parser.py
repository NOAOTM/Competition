import re
from pathlib import Path


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_text(path: Path) -> str:
    import fitz

    document = fitz.open(path)
    pages: list[list[tuple[float, float, float, float, str]]] = []
    for page in document:
        blocks = []
        for block in page.get_text("blocks"):
            if len(block) < 5 or not str(block[4]).strip():
                continue
            x0, y0, x1, y1 = map(float, block[:4])
            if y0 < page.rect.height * 0.045 or y1 > page.rect.height * 0.955:
                continue
            blocks.append((x0, y0, x1, y1, str(block[4]).strip()))
        pages.append(blocks)

    repeated: dict[str, int] = {}
    for blocks in pages:
        if not blocks:
            continue
        for block in (min(blocks, key=lambda row: row[1]), max(blocks, key=lambda row: row[3])):
            key = re.sub(r"\s+", " ", block[4]).strip().lower()
            repeated[key] = repeated.get(key, 0) + 1
    page_texts = []
    for page in document:
        blocks = pages[page.number]
        if not blocks:
            page_texts.append("")
            continue
        rows = [block for block in blocks if repeated.get(re.sub(r"\s+", " ", block[4]).strip().lower(), 0) < 2]
        midpoint = page.rect.width / 2
        left = [row for row in rows if row[0] < midpoint and row[2] < page.rect.width * 0.78]
        right = [row for row in rows if row[0] >= midpoint or row[2] >= page.rect.width * 0.78]
        full = [row for row in rows if row not in left and row not in right]
        if left and right:
            ordered = sorted(full, key=lambda row: row[1])
            body_y = [row[1] for row in left + right]
            top = [row for row in ordered if row[1] < min(body_y)]
            bottom = [row for row in ordered if row[1] >= max(body_y)]
            content = top + sorted(left, key=lambda row: row[1]) + sorted(right, key=lambda row: row[1]) + bottom
        else:
            content = sorted(rows, key=lambda row: (row[1], row[0]))
        page_texts.append("\n".join(row[4] for row in content))
    document.close()
    text = "\n\n".join(page_texts)
    if len(re.sub(r"\W", "", text)) < 100:
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                text = "\n\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)
        except Exception:
            pass
    if len(re.sub(r"\W", "", text)) < 100:
        import fitz
        import pytesseract
        from PIL import Image

        pages_ocr = []
        with fitz.open(path) as document:
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                pages_ocr.append(pytesseract.image_to_string(image, lang="chi_sim+eng"))
        text = "\n\n".join(pages_ocr)
    text = re.split(r"(?im)^\s*(references|bibliography|参考文献)\s*$", text)[0]
    return _clean(text)


def extract_document_text(path: str | Path) -> tuple[str, dict[str, object]]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(source)
        return text, {"filename": source.name, "format": "PDF", "characters": len(text)}
    if suffix == ".docx":
        from docx import Document

        document = Document(source)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        text += "\n" + "\n".join(" | ".join(cell.text for cell in row.cells) for table in document.tables for row in table.rows)
        text = _clean(text)
        return text, {"filename": source.name, "format": "DOCX", "characters": len(text)}
    if suffix == ".txt":
        text = _clean(source.read_text(encoding="utf-8", errors="replace"))
        return text, {"filename": source.name, "format": "TXT", "characters": len(text)}
    raise ValueError("仅支持 PDF、DOCX 和 TXT 文件")


def split_chunks(text: str, chunk_size: int, overlap: int, max_chunks: int) -> tuple[list[str], bool]:
    if chunk_size < 200 or overlap < 0 or overlap >= chunk_size or max_chunks < 1:
        raise ValueError("分块配置无效")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    truncated = len(chunks) > max_chunks
    if truncated:
        def importance(item: tuple[int, str]) -> tuple[int, int]:
            index, chunk = item
            words = ("abstract", "introduction", "method", "result", "conclusion", "discussion", "摘要", "引言", "方法", "结果", "结论", "讨论")
            return (sum(chunk.lower().count(word) for word in words), -index)

        selected = sorted(sorted(enumerate(chunks), key=importance, reverse=True)[:max_chunks])
        chunks = [chunk for _, chunk in selected]
    return chunks, truncated
