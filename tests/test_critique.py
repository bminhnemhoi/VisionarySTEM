"""Tests for src.core.critique — Sprint 8.2."""
from unittest.mock import MagicMock
import pytest


def test_critique_threshold_constant():
    from src.core.critique import CritiqueEngine
    assert 0 < CritiqueEngine.REVIEW_THRESHOLD < 1


def test_critique_merge_into_blocks(sample_blocks):
    from src.core.critique import CritiqueEngine, BlockCritique
    eng = CritiqueEngine()
    critiques = [
        BlockCritique(block_id="block_001", critique_score=0.95, issues=[]),
        BlockCritique(block_id="block_002", critique_score=0.5, issues=["LaTeX nghi ngờ", "spoken_text thiếu đơn vị"]),
    ]
    merged = eng._merge_into_blocks(sample_blocks, critiques)

    b1 = next(b for b in merged if b.id == "block_001")
    assert b1.critique_score == 0.95
    assert b1.needs_review is False
    assert b1.critique_issues is None  # empty list → None

    b2 = next(b for b in merged if b.id == "block_002")
    assert b2.critique_score == 0.5
    assert b2.needs_review is True
    assert "LaTeX nghi ngờ" in b2.critique_issues


def test_critique_confidence_merging(sample_blocks):
    """Final confidence = 0.6 * gemini_conf + 0.4 * critique_score."""
    from src.core.critique import CritiqueEngine, BlockCritique
    eng = CritiqueEngine()
    blocks = [b for b in sample_blocks if b.id == "block_002"]  # confidence 0.99
    critiques = [BlockCritique(block_id="block_002", critique_score=0.5, issues=[])]
    merged = eng._merge_into_blocks(blocks, critiques)
    expected = round(0.6 * 0.99 + 0.4 * 0.5, 3)
    assert merged[0].confidence == expected


def test_critique_uses_cache(sample_blocks):
    """Second call should not invoke Gemini again."""
    from src.core.critique import CritiqueEngine, BlockCritique
    eng = CritiqueEngine()
    eng._cache["doc_x"] = [
        BlockCritique(block_id="block_001", critique_score=0.9, issues=[])
    ]
    result1 = eng.critique_blocks("doc_x", sample_blocks[:1])
    result2 = eng.critique_blocks("doc_x", sample_blocks[:1])
    # Both should return blocks with the cached critique applied
    assert result1[0].critique_score == 0.9
    assert result2[0].critique_score == 0.9


def test_critique_blocks_with_mocked_gemini(monkeypatch, sample_blocks):
    """Full flow with mocked Gemini call."""
    from src.core import critique as critique_module
    from src.core.critique import CritiqueEngine, CritiqueResult, BlockCritique

    eng = CritiqueEngine()
    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_response = MagicMock()
    mock_response.parsed = CritiqueResult(
        critiques=[
            BlockCritique(block_id="block_001", critique_score=0.92, issues=[]),
            BlockCritique(block_id="block_002", critique_score=0.65, issues=["spoken_text dài quá"]),
            BlockCritique(block_id="block_003", critique_score=0.88, issues=[]),
            BlockCritique(block_id="block_004", critique_score=0.9, issues=[]),
            BlockCritique(block_id="block_005", critique_score=0.85, issues=[]),
        ]
    )
    mock_engine.client.models.generate_content = MagicMock(return_value=mock_response)
    monkeypatch.setattr(critique_module, "get_engine", lambda: mock_engine)

    result = eng.critique_blocks("doc_test", sample_blocks)
    flagged = [b for b in result if b.needs_review]
    assert len(flagged) == 1
    assert flagged[0].id == "block_002"


def test_critique_handles_empty_blocks():
    from src.core.critique import CritiqueEngine
    eng = CritiqueEngine()
    assert eng.critique_blocks("doc_empty", []) == []


def test_critique_graceful_degradation_on_gemini_error(monkeypatch, sample_blocks):
    """If Gemini fails, return blocks unmodified instead of crashing."""
    from src.core import critique as critique_module
    from src.core.critique import CritiqueEngine

    eng = CritiqueEngine()
    mock_engine = MagicMock()
    mock_engine.model = "gemini-2.5-flash"
    mock_engine.client.models.generate_content = MagicMock(side_effect=RuntimeError("API down"))
    monkeypatch.setattr(critique_module, "get_engine", lambda: mock_engine)

    result = eng.critique_blocks("doc_err", sample_blocks)
    # Returns original blocks unmodified
    assert len(result) == len(sample_blocks)
    assert all(b.critique_score is None for b in result)
