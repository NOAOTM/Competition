import json
import re
from pathlib import Path


def _items(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item.get("text", item.get("name", item)) if isinstance(item, dict) else item) for item in values]


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _write_graph(knowledge: dict, directory: Path) -> list[str]:
    from graphviz import Digraph

    nodes = knowledge.get("logic_nodes", [])
    edges = knowledge.get("logic_edges", [])
    graph = Digraph("logic", format="png")
    graph.attr(rankdir="LR", bgcolor="white", fontname="Noto Sans CJK SC", dpi="140")
    graph.attr("node", shape="box", style="rounded,filled", fillcolor="#E8F3EC", color="#6F9F83", fontname="Noto Sans CJK SC")
    graph.attr("edge", color="#55816A", fontname="Noto Sans CJK SC")
    ids = []
    for index, value in enumerate(nodes):
        if isinstance(value, dict):
            node_id = str(value.get("id", f"n{index}"))
            label = str(value.get("label", value.get("text", value.get("name", f"节点 {index + 1}"))))
        else:
            node_id = f"n{index}"
            label = str(value)
        ids.append(node_id)
        graph.node(node_id, label=label)
    if not ids:
        graph.node("n0", label="未提取到可视化逻辑节点")
        ids = ["n0"]
    for index, value in enumerate(edges):
        if isinstance(value, dict):
            source = str(value.get("source", value.get("from", "")))
            target = str(value.get("target", value.get("to", "")))
            label = str(value.get("label", ""))
            if source not in ids and source.isdigit():
                source = f"n{source}"
            if target not in ids and target.isdigit():
                target = f"n{target}"
            if source in ids and target in ids:
                graph.edge(source, target, label=label)
    dot_path = directory / "logic_diagram.dot"
    dot_path.write_text(graph.source, encoding="utf-8")
    graph.render(filename=str(directory / "logic_diagram"), cleanup=True)
    return ["logic_diagram.dot", "logic_diagram.png"]


def _make_presentation(knowledge: dict, directory: Path, source_name: str) -> list[str]:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    title = str(knowledge.get("meta", {}).get("title", source_name)) if isinstance(knowledge.get("meta"), dict) else source_name
    summary = str(knowledge.get("one_sentence_summary", "原文未说明"))
    sections = [
        ("背景与研究意义", _items(knowledge.get("core_concepts"))),
        ("研究问题", [summary]),
        ("研究设计与方法", _items(knowledge.get("logic_nodes"))),
        ("数据与实验", _items(knowledge.get("logic_edges"))),
        ("主要发现", [summary]),
        ("结果解释", _items(knowledge.get("core_concepts"))),
        ("研究逻辑链", _items(knowledge.get("logic_edges"))),
        ("关键公式", _items(knowledge.get("formulas"))),
        ("理论与实践贡献", _items(knowledge.get("core_concepts"))),
        ("局限性", _items(knowledge.get("uncertainties"))),
        ("证据与不确定性", _items(knowledge.get("uncertainties"))),
        ("可讨论问题", ["研究设计是否充分回答了研究问题？", "结论适用范围是否受数据或方法限制？", "哪些结果值得进一步复现？"]),
        ("后续研究方向", _items(knowledge.get("uncertainties"))),
        ("结论回顾", [summary]),
    ]
    headings = [("组会导读", [title, summary, "由真知 Agent 根据用户上传的原文生成，请以原文复核。"])] + sections
    for heading, lines in headings:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(248, 251, 248)
        title_box = slide.shapes.add_textbox(Inches(0.65), Inches(0.35), Inches(12), Inches(0.7))
        title_frame = title_box.text_frame
        title_frame.text = heading
        title_frame.paragraphs[0].font.name = "Noto Sans CJK SC"
        title_frame.paragraphs[0].font.size = Pt(28)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = RGBColor(38, 105, 75)
        body = slide.shapes.add_textbox(Inches(0.85), Inches(1.45), Inches(11.6), Inches(5.3))
        frame = body.text_frame
        frame.word_wrap = True
        points = [line for line in lines if line] or ["原文未说明，请结合全文人工核实。"]
        while len(points) < 3:
            points.append("本部分未从当前提取片段中确认，需回到原文核对。")
        for index, line in enumerate(points[:5]):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = line[:500]
            paragraph.font.name = "Noto Sans CJK SC"
            paragraph.font.size = Pt(20)
            paragraph.font.color.rgb = RGBColor(46, 58, 50)
            paragraph.space_after = Pt(16)
        footer = slide.shapes.add_textbox(Inches(0.7), Inches(7.03), Inches(12), Inches(0.25))
        footer.text_frame.text = f"文献导读 · {source_name} · {len(presentation.slides):02d}"
        footer.text_frame.paragraphs[0].font.name = "Noto Sans CJK SC"
        footer.text_frame.paragraphs[0].font.size = Pt(9)
        footer.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
        slide.notes_slide.notes_text_frame.text = f"讲稿备注：本页内容根据上传文献提取，讲解前请核对原文。主题：{heading}。"
    path = directory / "group_meeting.pptx"
    presentation.save(path)
    return [path.name]


def generate_research_files(knowledge: dict, directory: Path, source_name: str, warnings: list[str]) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "knowledge.json"
    json_path.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
    concepts = "\n".join(f"- {item}" for item in _items(knowledge.get("core_concepts"))) or "- 原文未说明"
    nodes = "\n".join(f"- {item}" for item in _items(knowledge.get("logic_nodes"))) or "- 原文未说明"
    formulas = "\n".join(f"- $${item}$$" for item in _items(knowledge.get("formulas"))) or "- 原文未说明"
    uncertainties = "\n".join(f"- {item}" for item in _items(knowledge.get("uncertainties"))) or "- 原文未说明"
    markdown = (
        f"# 文献导读：{source_name}\n\n"
        f"## 一句话总结\n{knowledge.get('one_sentence_summary', '原文未说明')}\n\n"
        f"## 核心概念\n{concepts}\n\n"
        f"## 逻辑节点\n{nodes}\n\n"
        f"## 公式与说明\n{formulas}\n\n"
        "公式符号、单位和适用条件请结合原文核验；未明确的信息标注为“原文未说明”。\n\n"
        f"## 不确定性与局限\n{uncertainties}\n"
    )
    (directory / "knowledge_explained.md").write_text(markdown, encoding="utf-8")
    outline_headings = [
        "导读", "背景与研究意义", "研究问题", "研究设计与方法", "数据与实验",
        "主要发现", "结果解释", "研究逻辑链", "关键公式", "理论与实践贡献",
        "局限性", "证据与不确定性", "可讨论问题", "后续研究方向", "结论回顾",
    ]
    outline = "# 组会 PPT 大纲\n\n" + "\n".join(
        f"{index}. {heading}" for index, heading in enumerate(outline_headings, 1)
    )
    (directory / "ppt_outline.md").write_text(outline + "\n", encoding="utf-8")
    (directory / "run.log").write_text("质量门禁：仅提供警告，不阻断结果生成。\n" + "\n".join(warnings), encoding="utf-8")
    files = [json_path.name, "knowledge_explained.md", "ppt_outline.md", "run.log"]
    try:
        files.extend(_write_graph(knowledge, directory))
    except Exception as exc:
        warnings.append(f"逻辑图 PNG 生成失败：{exc}")
        (directory / "run.log").write_text("\n".join(warnings), encoding="utf-8")
    try:
        files.extend(_make_presentation(knowledge, directory, source_name))
    except Exception as exc:
        warnings.append(f"组会 PPTX 生成失败：{exc}")
        (directory / "run.log").write_text("\n".join(warnings), encoding="utf-8")
    return files
