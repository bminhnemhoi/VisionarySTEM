"""
VisionarySTEM Document QA — Sprint 6.4
========================================
Free-form Q&A over an analyzed document. Different from /chat (multi-turn tutor)
because this is single-shot, no history, optimized for fact lookups.

Use case: "Tài liệu này nói về cái gì?" / "Có bao nhiêu công thức?" / "Hằng số trong công thức 3 là gì?"
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field

from src.api.schemas import DocumentAnalysisResponse
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


QA_PROMPT_TEMPLATE = """Bạn là trợ lý nghiên cứu cho sinh viên khiếm thị Việt Nam.

Tài liệu được phân tích:
- File: {filename}
- {n_blocks} block (text, math, chart, table, figure)

Nội dung chi tiết:
{block_dump}

Câu hỏi của người dùng: "{question}"

QUY TẮC TRẢ LỜI:
1. Trả lời 100% bằng tiếng Việt tự nhiên, ngắn gọn (≤ 4 câu).
2. Nếu thông tin có trong tài liệu, trả lời cụ thể + cite block ID.
3. Nếu thông tin KHÔNG có, trả lời thẳng: "Tài liệu không có thông tin về điều này."
4. Tuyệt đối không bịa đặt — đây là quy tắc bất di bất dịch cho người khiếm thị.
5. Công thức đọc bằng tiếng Việt tự nhiên (không "F equals m a").

Trả về JSON: {{
  "answer": "câu trả lời",
  "cited_blocks": ["block_002", "block_005"],
  "confidence": 0.0-1.0
}}"""


class QAResponse(BaseModel):
    answer: str
    cited_blocks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


def _build_block_dump(doc: DocumentAnalysisResponse, max_chars: int = 8000) -> str:
    """Compact representation for the QA prompt — fits Gemini context window."""
    lines = []
    total = 0
    for b in doc.content_blocks:
        latex_part = f" | LaTeX: {b.latex}" if b.latex else ""
        line = (
            f"[{b.id} type={b.type} region={b.coordinates.region} page={b.coordinates.page}]: "
            f"{b.spoken_text}{latex_part}"
        )
        if total + len(line) > max_chars:
            lines.append(f"... (đã cắt {len(doc.content_blocks) - len(lines)} block còn lại để tiết kiệm token)")
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


def answer_question(doc: DocumentAnalysisResponse, question: str) -> QAResponse:
    """
    Single-shot QA over the document.
    Returns answer + cited block IDs + confidence.
    """
    engine = get_engine()
    prompt = QA_PROMPT_TEMPLATE.format(
        filename=doc.document_metadata.filename,
        n_blocks=len(doc.content_blocks),
        block_dump=_build_block_dump(doc),
        question=question.strip(),
    )

    try:
        response = engine.client.models.generate_content(
            model=engine.model,
            contents=[types.Part(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QAResponse,
                temperature=0.2,
                max_output_tokens=500,
            ),
        )
        result = response.parsed
        if result is None:
            try:
                result = QAResponse(**json.loads(response.text))
            except Exception as e:
                logger.error(f"QA parse failed: {e}")
                return QAResponse(
                    answer="Xin lỗi, không xử lý được câu hỏi. Vui lòng thử lại.",
                    cited_blocks=[],
                    confidence=0.0,
                )
    except Exception as e:
        logger.error(f"QA Gemini call failed: {e}", exc_info=True)
        return QAResponse(
            answer="Hệ thống đang bận. Vui lòng thử lại sau.",
            cited_blocks=[],
            confidence=0.0,
        )

    # Validate cited blocks
    valid_ids = {b.id for b in doc.content_blocks}
    result.cited_blocks = [bid for bid in result.cited_blocks if bid in valid_ids]
    return result
