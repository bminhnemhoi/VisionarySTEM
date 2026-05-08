"""Tests for src.core.qa — Sprint 6.4 single-shot QA."""
from unittest.mock import MagicMock
import pytest


def _make_doc(sample_blocks):
    from src.api.schemas import DocumentAnalysisResponse, DocumentMetadata, SpatialIndex
    return DocumentAnalysisResponse(
        document_metadata=DocumentMetadata(
            filename="test.pdf", total_pages=1, processing_time_ms=1000,
            model_used="gemini-2.5-flash",
        ),
        content_blocks=sample_blocks,
        spatial_index=SpatialIndex(regions={}),
    )


def test_build_block_dump_truncates(sample_blocks):
    """Long doc should fit max_chars and indicate truncation."""
    from src.core.qa import _build_block_dump
    doc = _make_doc(sample_blocks * 50)  # 250 blocks
    dump = _build_block_dump(doc, max_chars=2000)
    assert "đã cắt" in dump
    assert len(dump) <= 2200


def test_qa_with_mocked_gemini(monkeypatch, sample_blocks):
    """Full QA flow with mocked Gemini."""
    from src.core import qa as qa_module
    from src.core.qa import answer_question, QAResponse

    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.parsed = QAResponse(
        answer="Định luật hai Niu-tơn cho biết lực bằng khối lượng nhân gia tốc.",
        cited_blocks=["block_002", "block_003"],
        confidence=0.92,
    )
    mock_engine.client.models.generate_content = MagicMock(return_value=mock_response)
    monkeypatch.setattr(qa_module, "get_engine", lambda: mock_engine)

    doc = _make_doc(sample_blocks)
    result = answer_question(doc, "F=ma là gì?")
    assert result.answer.startswith("Định luật")
    assert "block_002" in result.cited_blocks
    assert result.confidence == 0.92


def test_qa_filters_invalid_cited_blocks(monkeypatch, sample_blocks):
    """Cited block IDs not in doc should be removed."""
    from src.core import qa as qa_module
    from src.core.qa import answer_question, QAResponse

    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.parsed = QAResponse(
        answer="OK",
        cited_blocks=["block_002", "block_FAKE", "block_003"],
        confidence=0.8,
    )
    mock_engine.client.models.generate_content = MagicMock(return_value=mock_response)
    monkeypatch.setattr(qa_module, "get_engine", lambda: mock_engine)

    doc = _make_doc(sample_blocks)
    result = answer_question(doc, "Q?")
    assert result.cited_blocks == ["block_002", "block_003"]


def test_qa_graceful_on_gemini_error(monkeypatch, sample_blocks):
    """Gemini failure → graceful fallback, no crash."""
    from src.core import qa as qa_module
    from src.core.qa import answer_question

    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_engine.client.models.generate_content = MagicMock(side_effect=RuntimeError("API down"))
    monkeypatch.setattr(qa_module, "get_engine", lambda: mock_engine)

    doc = _make_doc(sample_blocks)
    result = answer_question(doc, "Q?")
    assert result.confidence == 0.0
    assert "bận" in result.answer.lower() or "thử lại" in result.answer.lower()
