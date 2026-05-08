"""Test Pydantic schemas — they're the API contract, must not break silently."""
import pytest
from pydantic import ValidationError


def test_coordinates_valid(sample_block_dict):
    from src.api.schemas import Coordinates
    c = Coordinates(**sample_block_dict["coordinates"])
    assert c.page == 1
    assert c.region == "center"


def test_coordinates_out_of_range():
    from src.api.schemas import Coordinates
    with pytest.raises(ValidationError):
        Coordinates(page=1, x=150, y=20, w=30, h=10, region="center")


def test_content_block_optional_latex(sample_block_dict):
    from src.api.schemas import ContentBlock
    sample_block_dict["latex"] = None
    sample_block_dict["type"] = "text"
    block = ContentBlock(**sample_block_dict)
    assert block.latex is None
    assert block.language == "vi"


def test_content_block_invalid_type(sample_block_dict):
    from src.api.schemas import ContentBlock
    sample_block_dict["type"] = "diagram"  # not in enum
    with pytest.raises(ValidationError):
        ContentBlock(**sample_block_dict)


def test_content_block_confidence_clamp(sample_block_dict):
    from src.api.schemas import ContentBlock
    sample_block_dict["confidence"] = 1.5
    with pytest.raises(ValidationError):
        ContentBlock(**sample_block_dict)


def test_full_response_roundtrip(sample_blocks):
    from src.api.schemas import (
        DocumentAnalysisResponse, DocumentMetadata, SpatialIndex,
    )
    response = DocumentAnalysisResponse(
        document_metadata=DocumentMetadata(
            filename="test.pdf", total_pages=1, processing_time_ms=1000,
            model_used="gemini-2.5-flash",
        ),
        content_blocks=sample_blocks,
        spatial_index=SpatialIndex(regions={"center": ["block_002", "block_003"]}),
    )
    dumped = response.model_dump()
    assert dumped["document_metadata"]["filename"] == "test.pdf"
    assert len(dumped["content_blocks"]) == 5
