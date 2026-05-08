"""Test new accessibility fields added to ContentBlock in Sprint 4."""
import pytest


def test_extended_block_with_optional_fields(sample_block_dict):
    """All Sprint 4 fields are Optional → backward-compat."""
    from src.api.schemas import ContentBlock
    block = ContentBlock(**sample_block_dict)
    assert block.reading_order is None
    assert block.alt_text_long is None
    assert block.mathml is None
    assert block.aria_role is None


def test_extended_block_with_all_fields(sample_block_dict):
    sample_block_dict.update({
        "reading_order": 3,
        "importance": "primary",
        "alt_text_long": "Mô tả chi tiết biểu đồ đường thẳng đi qua gốc tọa độ thể hiện quan hệ tỉ lệ thuận.",
        "mathml": "<math><mi>F</mi><mo>=</mo><mi>m</mi><mo>·</mo><mi>a</mi></math>",
        "parent_id": "block_table_001",
        "aria_role": "math",
    })
    from src.api.schemas import ContentBlock
    block = ContentBlock(**sample_block_dict)
    assert block.reading_order == 3
    assert block.importance == "primary"
    assert block.aria_role == "math"


def test_invalid_importance(sample_block_dict):
    """importance must be one of: primary, secondary, decorative."""
    from src.api.schemas import ContentBlock
    from pydantic import ValidationError
    sample_block_dict["importance"] = "ultra-mega"
    with pytest.raises(ValidationError):
        ContentBlock(**sample_block_dict)
