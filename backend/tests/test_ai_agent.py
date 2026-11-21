from app.services.ai_agent import REQUIRED_KEYS, parse_json_response
from app.services.llm_client import _clean_response
from app.services.pdf_parser import split_chunks


def test_json_parser_removes_reasoning_fence_and_fills_schema():
    parsed = parse_json_response(
        '<think>hidden notes</think>\n```json\n{"one_sentence_summary":"研究摘要","meta":{}}\n```'
    )
    assert parsed["one_sentence_summary"] == "研究摘要"
    assert all(key in parsed for key in REQUIRED_KEYS)
    assert parsed["core_concepts"] == []


def test_reasoning_tokens_are_not_returned():
    assert _clean_response("<think>private</think> final answer") == "final answer"


def test_long_text_is_capped_and_marked_truncated():
    chunks, truncated = split_chunks("摘要与方法\n" + "学术内容。" * 500, 300, 30, 3)
    assert truncated is True
    assert len(chunks) == 3
    assert all(len(chunk) <= 300 for chunk in chunks)
