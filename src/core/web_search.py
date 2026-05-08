"""
VisionarySTEM Web Search Agent — Phase 2.

Dùng Gemini built-in `google_search` tool để search internet, return summary +
grounding citations. KHÔNG cần API key thứ 2 (Tavily, Brave...).

Ý nghĩa cho dự án: User nói "tìm tài liệu chất béo hoá 12 trên mạng" → AI tự
search Google qua Gemini → tóm tắt tiếng Việt + cite 3-5 nguồn → user chọn nguồn
nào để analyze sâu (qua /analyze-url).

Reference: https://ai.google.dev/gemini-api/docs/grounding
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field

from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


class WebSource(BaseModel):
    """Một nguồn từ Google grounding."""
    title: str
    url: str
    snippet: Optional[str] = Field(default=None, description="Đoạn trích ngắn (nếu có)")


class WebSearchResult(BaseModel):
    """Kết quả tổng hợp từ web search."""
    query: str
    summary: str = Field(description="Tóm tắt tiếng Việt, đã chuẩn bị cho TTS")
    sources: list[WebSource]
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Gợi ý hành động: 'phân tích nguồn 1', 'tìm thêm về X'...",
    )
    elapsed_ms: int = Field(description="Thời gian search + summarize")


_SEARCH_SYSTEM_PROMPT = """Bạn là AI search assistant tiếng Việt cho sinh viên khiếm thị Việt Nam.

NHIỆM VỤ:
Khi user hỏi tìm thông tin/tài liệu STEM trên mạng, dùng google_search tool để tra cứu,
sau đó tóm tắt kết quả bằng tiếng Việt tự nhiên cho người nghe.

QUY TẮC TÓM TẮT:
1. Trả lời 100% tiếng Việt tự nhiên, dù nguồn là tiếng Anh.
2. Câu ngắn (≤25 từ/câu) cho TTS đọc dễ hiểu.
3. TỔNG ĐỘ DÀI: 4-7 câu. KHÔNG cụt ngủn, KHÔNG lê thê.
4. Cấu trúc:
   - Mở đầu: "Tôi tìm được X nguồn về [chủ đề]."
   - Tóm tắt nội dung chính từ các nguồn (gộp ý, không list từng nguồn).
   - Kết: "Bạn muốn tôi phân tích sâu nguồn nào, hoặc tìm thêm khía cạnh khác?"
5. Công thức toán đọc tiếng Việt: "F = m a" → "Lực bằng khối lượng nhân gia tốc".
6. KHÔNG dùng markdown bullet (*, -). Thay bằng "thứ nhất", "thứ hai".
7. KHÔNG dùng emoji.
8. KHÔNG đọc URL trực tiếp trong summary — frontend sẽ liệt kê sources riêng.

NẾU KHÔNG TÌM ĐƯỢC GÌ HỮU ÍCH:
"Xin lỗi, tôi không tìm được tài liệu phù hợp về [chủ đề]. Bạn thử từ khoá khác hoặc tải file trực tiếp nhé."
"""


def _extract_sources_from_grounding(response) -> list[WebSource]:
    """
    Parse `grounding_metadata.grounding_chunks` từ Gemini response.

    Format chunk: { web: { uri: str, title: str } } per item.
    """
    sources: list[WebSource] = []
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return sources
        gm = getattr(candidates[0], "grounding_metadata", None)
        if not gm:
            return sources
        chunks = getattr(gm, "grounding_chunks", None) or []
        seen_urls: set[str] = set()
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            uri = getattr(web, "uri", None) or ""
            title = getattr(web, "title", None) or "Untitled"
            if not uri or uri in seen_urls:
                continue
            seen_urls.add(uri)
            sources.append(WebSource(title=title, url=uri))
    except Exception as e:
        logger.warning(f"[web_search] grounding parse warn: {e}")
    return sources


async def google_search(query: str, max_sources: int = 5) -> WebSearchResult:
    """
    Search web qua Gemini grounding + summarize tiếng Việt.

    Args:
        query: câu hỏi/từ khoá tiếng Việt từ user
        max_sources: cap số sources trả về (Google thường trả 5-10 chunks)

    Returns:
        WebSearchResult có summary + sources + suggested_actions
    """
    if not query or not query.strip():
        raise ValueError("Query rỗng")

    start = time.time()
    engine = get_engine()

    # Build user message — thêm hint về Việt Nam education context
    user_msg = (
        f"Tìm tài liệu/thông tin về: {query}\n\n"
        f"Ưu tiên nguồn tiếng Việt (vietjack, hocmai, wikipedia tiếng Việt, vndoc...). "
        f"Sau đó tóm tắt cho sinh viên khiếm thị nghe."
    )

    # Note: với google_search tool, Gemini KHÔNG cho dùng response_schema
    # → phải parse free text response. response.text chính là summary.
    response = engine.client.models.generate_content(
        model=engine.model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_SEARCH_SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )

    summary = (response.text or "").strip()
    if not summary:
        summary = (
            f"Xin lỗi, tôi không tìm được tài liệu phù hợp về {query}. "
            f"Bạn thử từ khoá khác hoặc tải file trực tiếp nhé."
        )

    sources = _extract_sources_from_grounding(response)[:max_sources]

    # Suggested follow-up actions
    suggested_actions: list[str] = []
    if sources:
        # Top source → suggest analyze
        suggested_actions.append(
            f"Phân tích sâu nguồn 1: {sources[0].title[:60]}"
        )
        if len(sources) > 1:
            suggested_actions.append("Đọc nguồn khác")
    suggested_actions.append("Tìm thêm chủ đề khác")

    elapsed_ms = int((time.time() - start) * 1000)
    logger.info(
        f"[web_search] query={query!r} → {len(sources)} sources, "
        f"summary_len={len(summary)}, elapsed={elapsed_ms}ms"
    )

    return WebSearchResult(
        query=query,
        summary=summary,
        sources=sources,
        suggested_actions=suggested_actions,
        elapsed_ms=elapsed_ms,
    )
