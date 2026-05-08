"""Tests for src.core.tutor — Sprint 8.1."""
from unittest.mock import MagicMock, patch
import pytest


def _make_doc_response(sample_blocks):
    from src.api.schemas import DocumentAnalysisResponse, DocumentMetadata, SpatialIndex
    return DocumentAnalysisResponse(
        document_metadata=DocumentMetadata(
            filename="test.pdf", total_pages=1, processing_time_ms=1000,
            model_used="gemini-2.5-flash",
        ),
        content_blocks=sample_blocks,
        spatial_index=SpatialIndex(regions={"center": ["block_002", "block_003"]}),
    )


def test_tutor_session_lifecycle(sample_blocks):
    from src.core.tutor import TutorEngine
    tutor = TutorEngine()
    doc = _make_doc_response(sample_blocks)
    tutor.register_document("doc_a", doc)
    sid = tutor.new_session()
    assert isinstance(sid, str)
    assert tutor.get_history(sid) == []


def test_tutor_chat_unknown_document_raises(sample_blocks):
    from src.core.tutor import TutorEngine
    tutor = TutorEngine()
    with pytest.raises(ValueError, match="not registered"):
        tutor.chat("nonexistent", "sid", "Hello")


def test_tutor_chat_appends_history(monkeypatch, sample_blocks):
    """Mock Gemini, verify history grows."""
    from src.core import tutor as tutor_module
    from src.core.tutor import TutorEngine, GeminiChatReply

    tutor = TutorEngine()
    doc = _make_doc_response(sample_blocks)
    tutor.register_document("doc_a", doc)

    # Mock Gemini reply
    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.parsed = GeminiChatReply(
        reply_text="Định luật hai Niu-tơn cho biết lực bằng khối lượng nhân gia tốc.",
        cited_blocks=["block_002"],
        suggested_followups=["Cho ví dụ thực tế?", "Giải thích đơn giản hơn?"],
    )
    mock_engine.client.models.generate_content = MagicMock(return_value=mock_response)
    monkeypatch.setattr(tutor_module, "get_engine", lambda: mock_engine)

    sid = "session_1"
    reply = tutor.chat("doc_a", sid, "F=ma là gì?")
    assert reply.reply_text.startswith("Định luật")
    assert reply.cited_blocks == ["block_002"]
    assert len(reply.suggested_followups) >= 1

    history = tutor.get_history(sid)
    assert len(history) == 2  # user + assistant
    assert history[0].role == "user"
    assert history[1].role == "assistant"


def test_tutor_filters_invalid_cited_blocks(monkeypatch, sample_blocks):
    """Cited block IDs that don't exist in doc should be removed."""
    from src.core import tutor as tutor_module
    from src.core.tutor import TutorEngine, GeminiChatReply

    tutor = TutorEngine()
    doc = _make_doc_response(sample_blocks)
    tutor.register_document("doc_b", doc)

    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.parsed = GeminiChatReply(
        reply_text="OK",
        cited_blocks=["block_002", "block_999_fake", "block_003"],
        suggested_followups=[],
    )
    mock_engine.client.models.generate_content = MagicMock(return_value=mock_response)
    monkeypatch.setattr(tutor_module, "get_engine", lambda: mock_engine)

    reply = tutor.chat("doc_b", "s", "Q?")
    # block_999_fake removed
    assert reply.cited_blocks == ["block_002", "block_003"]


def test_tutor_reset_session(sample_blocks):
    from src.core.tutor import TutorEngine
    tutor = TutorEngine()
    doc = _make_doc_response(sample_blocks)
    tutor.register_document("doc_c", doc)
    sid = tutor.new_session()
    tutor._sessions[sid] = [object()]  # type: ignore - just needs to be non-empty
    assert len(tutor.get_history(sid)) == 1
    tutor.reset_session(sid)
    assert tutor.get_history(sid) == []


def test_block_summaries_truncates_long_docs(sample_blocks):
    """If doc has >max_blocks, summary should still fit."""
    from src.core.tutor import TutorEngine
    tutor = TutorEngine()
    # Replicate to exceed default 30
    big_doc = _make_doc_response(sample_blocks * 10)  # 50 blocks
    summary = tutor._build_block_summaries(big_doc, max_blocks=30)
    assert "+20 block khác" in summary or "+ 20" in summary or "(+" in summary
