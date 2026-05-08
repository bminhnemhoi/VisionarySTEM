"""Test document processor: page count, schema conversion, async pipeline."""
import asyncio
import pytest


def test_get_page_count_image(tmp_path):
    """Single image → 1 page."""
    # We don't actually run on a real image; just test the suffix branch
    from src.core.document_processor import _get_page_count
    fake_png = tmp_path / "fake.png"
    fake_png.write_bytes(b"not-a-real-png")
    assert _get_page_count(fake_png) == 1


def test_build_spatial_index(sample_blocks):
    from src.core.document_processor import _build_spatial_index
    idx = _build_spatial_index(sample_blocks)
    # 5 blocks split across regions: top-center(1), center(2), bottom-center(1), bottom-left(1)
    assert "center" in idx.regions
    assert len(idx.regions["center"]) == 2


def test_convert_gemini_to_schema():
    """GeminiContentBlock → ContentBlock conversion preserves all fields."""
    from src.core.document_processor import _convert_gemini_to_schema
    from src.core.gemini_engine import GeminiContentBlock, GeminiCoordinates

    gb = GeminiContentBlock(
        id="x", type="math", raw_content="F=ma", latex="F=ma",
        spoken_text="lực bằng khối lượng nhân gia tốc", confidence=0.9,
        coordinates=GeminiCoordinates(page=2, x=10, y=20, w=30, h=15, region="center"),
    )
    blocks = _convert_gemini_to_schema([gb], page_override=5)
    assert len(blocks) == 1
    assert blocks[0].coordinates.page == 5  # override applied
    assert blocks[0].language == "vi"


def test_renumber_blocks_globally():
    """Multi-page blocks should get global block_001, block_002, ... ordering."""
    from src.core.document_processor import _renumber_blocks_globally
    from src.core.gemini_engine import GeminiContentBlock, GeminiCoordinates, GeminiAnalysisResult

    def mk(idx, page):
        return GeminiContentBlock(
            id=f"raw_{idx}", type="text", raw_content=f"c{idx}", latex=None,
            spoken_text=f"câu {idx}", confidence=0.9,
            coordinates=GeminiCoordinates(page=page, x=10, y=10, w=10, h=10, region="top-left"),
        )

    # page 1 has 2 blocks, page 0 has 1 block (intentionally out of order to test sorting)
    pages = [
        (1, GeminiAnalysisResult(content_blocks=[mk(0, 2), mk(1, 2)])),
        (0, GeminiAnalysisResult(content_blocks=[mk(2, 1)])),
    ]
    result = _renumber_blocks_globally(pages)
    assert len(result) == 3
    # Sorted by page → page 1 first, page 2 second
    assert result[0].coordinates.page == 1
    assert result[0].id == "block_001"
    assert result[1].id == "block_002"
    assert result[2].id == "block_003"


@pytest.mark.asyncio
async def test_analyze_file_async_with_mock(mock_gemini_engine, tmp_path):
    """End-to-end async pipeline with a fake 1-page PDF."""
    import fitz
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 100), "Test page", fontsize=14)
    doc.save(str(pdf_path))
    doc.close()

    from src.core.document_processor import analyze_file_async
    result = await analyze_file_async(str(pdf_path))
    assert result.document_metadata.total_pages == 1
    assert len(result.content_blocks) == 5  # mock returns 5 blocks
    # Block ids renumbered globally
    assert result.content_blocks[0].id == "block_001"
