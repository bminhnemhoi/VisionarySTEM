"""
VisionarySTEM Text Analyzer — phân tích text-only documents (HTML articles).

Khác `document_processor.py`:
- KHÔNG render image qua PyMuPDF
- Đầu vào: raw text + title + source URL (sau trafilatura extract HTML)
- Gemini call với text-only prompt → blocks (text, math, list)

Flow:
  HTML page → trafilatura.extract() → clean text → analyze_text_async() → blocks
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field

from src.api.schemas import (
    ContentBlock,
    Coordinates,
    DocumentAnalysisResponse,
    DocumentMetadata,
    SpatialIndex,
)
from src.config import GEMINI_MODEL
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


# Schema cho Gemini structured output (text-only — không có coordinates)
class _GeminiTextBlock(BaseModel):
    id: str = Field(description="Mã khối: block_001, block_002, ...")
    type: str = Field(description="Loại: text (tiêu đề, đoạn văn, danh sách) hoặc math (công thức)")
    raw_content: str = Field(description="Nội dung gốc trích từ article")
    latex: Optional[str] = Field(default=None, description="Mã LaTeX (chỉ cho khối toán)")
    spoken_text: str = Field(description="Văn bản đọc tiếng Việt tự nhiên cho TTS")
    confidence: float = Field(description="0.0-1.0, độ tin cậy trích xuất")


class _GeminiTextResult(BaseModel):
    blocks: list[_GeminiTextBlock]


_TEXT_SYSTEM_PROMPT = """Bạn là AI phân tích bài viết web học liệu cho sinh viên khiếm thị Việt Nam.

NHIỆM VỤ:
Đọc text đã được trích xuất từ một trang web (sau khi đã bỏ nav/footer/ads), chia thành các block có cấu trúc.

QUY TẮC BLOCK:
1. Mỗi block là một đơn vị logic: tiêu đề, đoạn văn, công thức, danh sách, ví dụ.
2. Block ngắn (< 50 từ): nên gộp với block kề.
3. Block dài (> 200 từ): nên tách thành nhiều block.
4. Type:
   - "text": tiêu đề chương, đoạn văn thường, danh sách, mô tả
   - "math": công thức toán (có \\( \\) hoặc $...$ trong nguồn)

QUY TẮC SPOKEN_TEXT (CỰC KỲ QUAN TRỌNG):
- Tiếng Việt 100% tự nhiên, dễ nghe TTS.
- Công thức KHÔNG đọc kiểu tiếng Anh: "F = ma" → "Lực bằng khối lượng nhân gia tốc".
- Đơn vị đọc đầy đủ: "m/s²" → "mét trên giây bình phương", "kg" → "ki-lô-gam".
- Ký hiệu: "²" → "bình phương", "³" → "lập phương".
- Nếu nội dung gốc tiếng Anh → DỊCH spoken_text sang tiếng Việt tự nhiên.
- Mỗi block spoken_text 30-200 từ vừa phải.

QUY TẮC LATEX:
- Chỉ điền cho block type="math".
- Giữ nguyên LaTeX gốc nếu có (vd: F = m \\cdot a).
- Nếu nguồn dùng Unicode (∫, ∑, →), CONVERT sang LaTeX (\\int, \\sum, \\to).

QUY TẮC ID:
- block_001, block_002, ... theo thứ tự đọc.

CONFIDENCE:
- 0.95+ nếu nội dung rõ ràng, có cấu trúc tốt.
- 0.7-0.9 nếu hơi mơ hồ.
- < 0.7 nếu rất khó hiểu (không nên xuất hiện cho article educational).

KHÔNG output:
- Block trống (raw_content rỗng).
- Quảng cáo, footer, related articles, comment section.
- "Click here", "subscribe", navigation text.
"""


def _build_user_prompt(text: str, title: str, source_url: str) -> str:
    return f"""Bài viết tiêu đề: "{title}"
Nguồn: {source_url}

Nội dung text đã trích xuất:
---
{text}
---

Hãy chia thành các block có cấu trúc theo quy tắc trên. Mỗi block có id, type, raw_content, latex (nếu math), spoken_text tiếng Việt tự nhiên, confidence.
"""


def _gemini_text_analyze_sync(
    text: str,
    title: str,
    source_url: str,
) -> _GeminiTextResult:
    """Sync Gemini call. Wrapped trong asyncio.to_thread cho async usage."""
    engine = get_engine()
    response = engine.client.models.generate_content(
        model=engine.model,
        contents=_build_user_prompt(text, title, source_url),
        config=types.GenerateContentConfig(
            system_instruction=_TEXT_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=_GeminiTextResult,
            temperature=0.2,
            # 16k output token budget — đủ cho ~30 blocks dài. Article quá lớn sẽ
            # bị truncate input ở analyze_text_async (max_chars).
            max_output_tokens=16384,
        ),
    )
    parsed = response.parsed
    if parsed is None:
        # Fallback: thử parse partial JSON nếu structured output trả null
        try:
            parsed = _GeminiTextResult(**json.loads(response.text))
        except Exception as e:
            # Last resort: try recover partial blocks từ text response
            partial = _try_recover_partial_blocks(response.text)
            if partial:
                logger.warning(
                    f"[text_analyzer] Gemini JSON truncated, recovered {len(partial)} partial blocks"
                )
                parsed = _GeminiTextResult(blocks=partial)
            else:
                raise RuntimeError(f"Failed to parse Gemini text analyze response: {e}")
    return parsed


def _try_recover_partial_blocks(raw: str) -> list[_GeminiTextBlock]:
    """
    Khi Gemini truncate JSON giữa array, cố gắng cứu các block hoàn chỉnh đầu.
    Pattern: tìm các object {...} hoàn chỉnh trong "blocks": [ ... ].
    """
    import re
    blocks: list[_GeminiTextBlock] = []
    # Match each complete {...} object with required fields
    obj_pattern = re.compile(r'\{[^{}]*"id"[^{}]*"spoken_text"[^{}]*\}', re.DOTALL)
    for match in obj_pattern.finditer(raw):
        try:
            obj = json.loads(match.group())
            blocks.append(_GeminiTextBlock(**obj))
        except Exception:
            continue
    return blocks


async def analyze_text_async(
    text: str,
    title: str,
    source_url: str,
    max_chars: int = 15_000,
) -> DocumentAnalysisResponse:
    """
    Phân tích raw text (từ HTML article) thành DocumentAnalysisResponse.

    Args:
        text: clean text từ trafilatura
        title: tiêu đề article (hiển thị filename)
        source_url: URL gốc (cho log/audit)
        max_chars: cap text length để tránh exceed Gemini token budget.
                   ~15k chars ≈ 3750 input tokens, vừa cho 16k output budget.

    Returns:
        DocumentAnalysisResponse có content_blocks (text + math), spatial_index
        thưa (chỉ region "text-only").

    Raises:
        ValueError nếu text quá ngắn (< 200 chars — coi như không có nội dung).
        RuntimeError nếu Gemini lỗi.
    """
    if not text or len(text.strip()) < 200:
        raise ValueError(
            f"Text quá ngắn ({len(text.strip())} chars). "
            f"Có thể trang yêu cầu đăng nhập, dùng JavaScript, hoặc không có nội dung học."
        )

    # Truncate nếu quá dài (giữ đầu + cuối, bỏ giữa)
    original_len = len(text)
    if original_len > max_chars:
        head = text[: max_chars // 2]
        tail = text[-max_chars // 2 :]
        text = f"{head}\n\n[... phần giữa đã rút gọn ...]\n\n{tail}"
        logger.info(f"[text_analyzer] Truncated text from {original_len} to {len(text)} chars")

    start = time.time()
    try:
        result = await asyncio.to_thread(_gemini_text_analyze_sync, text, title, source_url)
    except Exception as e:
        logger.error(f"[text_analyzer] Gemini call failed: {e}", exc_info=True)
        raise RuntimeError(f"Phân tích text thất bại: {e}")

    elapsed_ms = int((time.time() - start) * 1000)

    # Convert Gemini blocks → schema ContentBlock
    # Coordinates set placeholder vì text không có spatial layout
    content_blocks: list[ContentBlock] = []
    for i, gb in enumerate(result.blocks, start=1):
        block_id = f"block_{i:03d}"  # renumber để đảm bảo nhất quán
        # Validate type
        btype = gb.type if gb.type in ("text", "math") else "text"
        # Validate confidence
        conf = max(0.0, min(1.0, gb.confidence))
        content_blocks.append(
            ContentBlock(
                id=block_id,
                type=btype,
                raw_content=gb.raw_content,
                latex=gb.latex if btype == "math" else None,
                spoken_text=gb.spoken_text,
                language="vi",
                confidence=conf,
                coordinates=Coordinates(
                    page=1,
                    x=0,
                    y=0,
                    w=100,
                    h=100,
                    region="text-only",
                ),
            )
        )

    # Spatial index thưa: tất cả block trong region "text-only"
    spatial_index = SpatialIndex(
        regions={"text-only": [b.id for b in content_blocks]}
    )

    metadata = DocumentMetadata(
        filename=title or "Bài viết web",
        total_pages=1,  # text article = 1 "page" logic
        processing_time_ms=elapsed_ms,
        model_used=f"{GEMINI_MODEL} (text-only via trafilatura)",
    )

    return DocumentAnalysisResponse(
        document_metadata=metadata,
        content_blocks=content_blocks,
        spatial_index=spatial_index,
    )
