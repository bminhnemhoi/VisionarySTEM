"""
Pytest fixtures for VisionarySTEM tests.

We mock GeminiEngine globally to avoid real API calls during unit/integration tests.
GEMINI_API_KEY is set to a dummy value so config.require_api_key() doesn't fail.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Set dummy API key BEFORE importing src.* modules
os.environ.setdefault("GEMINI_API_KEY", "test-key-pytest")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8501")

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------- Pydantic-light fixtures ----------

@pytest.fixture
def sample_block_dict() -> dict:
    """Minimal valid ContentBlock dict."""
    return {
        "id": "block_001",
        "type": "math",
        "raw_content": "F = ma",
        "latex": "F = ma",
        "spoken_text": "Lực bằng khối lượng nhân gia tốc.",
        "language": "vi",
        "confidence": 0.99,
        "coordinates": {
            "page": 1, "x": 35, "y": 30, "w": 30, "h": 8, "region": "center",
        },
    }


@pytest.fixture
def sample_blocks(sample_block_dict) -> list:
    """5 sample blocks across 3 regions / 3 types."""
    from src.api.schemas import ContentBlock
    base = sample_block_dict
    blocks = [
        {**base, "id": "block_001", "type": "text", "raw_content": "Định luật II Newton",
         "latex": None, "spoken_text": "Định luật hai Niu-tơn về chuyển động.",
         "coordinates": {"page": 1, "x": 10, "y": 5, "w": 80, "h": 8, "region": "top-center"}},
        {**base, "id": "block_002", "type": "math", "raw_content": "F = ma",
         "latex": "F = ma", "spoken_text": "Lực bằng khối lượng nhân gia tốc.",
         "coordinates": {"page": 1, "x": 35, "y": 30, "w": 30, "h": 8, "region": "center"}},
        {**base, "id": "block_003", "type": "math", "raw_content": "a = F/m",
         "latex": "a = \\frac{F}{m}", "spoken_text": "Gia tốc bằng lực chia cho khối lượng.",
         "coordinates": {"page": 1, "x": 35, "y": 42, "w": 30, "h": 8, "region": "center"}},
        {**base, "id": "block_004", "type": "chart", "raw_content": "Biểu đồ F vs a",
         "latex": None, "spoken_text": "Biểu đồ đường thẳng thể hiện quan hệ tỉ lệ thuận.",
         "coordinates": {"page": 1, "x": 15, "y": 55, "w": 70, "h": 35, "region": "bottom-center"}},
        {**base, "id": "block_005", "type": "text", "raw_content": "Ghi chú",
         "latex": None, "spoken_text": "Ghi chú trang một.",
         "coordinates": {"page": 1, "x": 10, "y": 92, "w": 80, "h": 5, "region": "bottom-left"}},
    ]
    return [ContentBlock(**b) for b in blocks]


# ---------- Mocked GeminiEngine ----------

@pytest.fixture
def mock_gemini_engine(monkeypatch, sample_blocks):
    """Replace get_engine() to return a mock that doesn't hit the network."""
    from src.core import gemini_engine as ge
    from src.core.gemini_engine import GeminiAnalysisResult, GeminiContentBlock, GeminiCoordinates

    def _to_gemini_block(b):
        return GeminiContentBlock(
            id=b.id, type=b.type, raw_content=b.raw_content, latex=b.latex,
            spoken_text=b.spoken_text, confidence=b.confidence,
            coordinates=GeminiCoordinates(
                page=b.coordinates.page, x=b.coordinates.x, y=b.coordinates.y,
                w=b.coordinates.w, h=b.coordinates.h, region=b.coordinates.region,
            ),
        )

    fake = MagicMock()
    fake.model = "gemini-2.5-flash"
    fake.analyze_image_bytes.return_value = GeminiAnalysisResult(
        content_blocks=[_to_gemini_block(b) for b in sample_blocks]
    )
    # Patch in BOTH the gemini_engine module AND any module that imported get_engine
    monkeypatch.setattr(ge, "get_engine", lambda: fake)
    from src.core import document_processor as dp
    monkeypatch.setattr(dp, "get_engine", lambda: fake)
    return fake


# ---------- FastAPI TestClient ----------

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from src.api.main import app
    return TestClient(app)
