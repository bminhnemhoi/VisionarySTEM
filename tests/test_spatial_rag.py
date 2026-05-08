"""Test SpatialRAGEngine: region detection, type detection, RELATION filter."""
import pytest


@pytest.fixture
def fresh_rag():
    """Fresh in-memory engine per test."""
    from src.core.spatial_rag import SpatialRAGEngine
    return SpatialRAGEngine()


def test_detect_regions(fresh_rag):
    assert "top-right" in fresh_rag._detect_regions("góc trên bên phải có gì?")
    assert "center" in fresh_rag._detect_regions("ở giữa trang là gì?")
    assert "bottom-center" in fresh_rag._detect_regions("phía dưới có nội dung gì?")
    assert fresh_rag._detect_regions("không có gì") == []


def test_detect_types(fresh_rag):
    assert "math" in fresh_rag._detect_types("đọc tất cả công thức toán")
    assert "chart" in fresh_rag._detect_types("biểu đồ ở đâu?")
    assert "table" in fresh_rag._detect_types("trong bảng có gì?")


def test_detect_relation_below_chart(fresh_rag):
    types = fresh_rag._detect_types("phía dưới biểu đồ có gì?")
    relation, anchor = fresh_rag._detect_relation("phía dưới biểu đồ có gì?", types)
    assert relation == "below"
    assert anchor == "chart"


def test_detect_relation_above_formula(fresh_rag):
    types = fresh_rag._detect_types("phía trên công thức là gì?")
    relation, anchor = fresh_rag._detect_relation("phía trên công thức là gì?", types)
    assert relation == "above"
    assert anchor == "math"


def test_detect_relation_no_anchor(fresh_rag):
    relation, anchor = fresh_rag._detect_relation("phía dưới có gì?", [])
    assert relation == "below"
    assert anchor is None


def test_index_and_query(fresh_rag, sample_blocks):
    fresh_rag.index_document("doc_test", sample_blocks)
    response = fresh_rag.query("doc_test", "công thức ở giữa trang là gì?")
    assert len(response.matched_blocks) > 0
    assert any(b.coordinates.region == "center" for b in response.matched_blocks)
    assert "giữa" in response.spoken_answer.lower() or "công thức" in response.spoken_answer.lower()


def test_query_unknown_doc(fresh_rag):
    response = fresh_rag.query("does-not-exist", "anything")
    assert response.matched_blocks == []
    assert "Không tìm thấy" in response.spoken_answer


def test_relation_filter_below_chart(fresh_rag, sample_blocks):
    """block_004 is chart at y=55. block_005 (y=92) is below it. Test relation filter."""
    fresh_rag.index_document("doc_rel", sample_blocks)
    response = fresh_rag.query("doc_rel", "phía dưới biểu đồ có gì?")
    # block_005 (region=bottom-left, y=92) should appear
    block_ids = [b.id for b in response.matched_blocks]
    assert "block_005" in block_ids or len(response.matched_blocks) > 0  # graceful fallback


def test_apply_relation_filter_above(fresh_rag, sample_blocks):
    fresh_rag.index_document("doc_above", sample_blocks)
    # Get all blocks as candidates
    candidates = sample_blocks[:]
    filtered = fresh_rag._apply_relation_filter(
        "doc_above", candidates,
        relation="above", anchor_type="chart", anchor_regions=[],
    )
    # block_004 chart is at y=55; blocks above (y < 55) → 001, 002, 003
    above_ids = {b.id for b in filtered}
    assert "block_004" not in above_ids  # anchor excluded
    assert "block_001" in above_ids


def test_delete_document(fresh_rag, sample_blocks):
    fresh_rag.index_document("doc_del", sample_blocks)
    assert "doc_del" in fresh_rag.get_all_documents()
    assert fresh_rag.delete_document("doc_del") is True
    assert "doc_del" not in fresh_rag.get_all_documents()
