"""
Tool registry cho Phase 3 planner.

Mỗi tool wrap 1 capability đã có (web_search, analyze_url, library_load, mock).
Planner pick tools + args dựa trên user request. Executor gọi từng tool.

Hiện tại tools KHÔNG chain args với nhau (mỗi step độc lập). Phase 3.5 sẽ thêm
data chaining (step output → next step input).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# Backend URL cho self-call. Trong dev = localhost. Trong production (HF Spaces /
# container deploy) — set thành public URL của backend hoặc giữ localhost vì
# tools.py chạy CÙNG container với endpoint, gọi self qua localhost OK.
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


@dataclass
class ToolSpec:
    """Tool metadata + handler."""
    name: str
    description: str  # cho planner đọc
    args_hint: str  # gợi ý args để planner output đúng
    handler: Callable[..., Awaitable[Any]]


# ---------- Tool handlers (wrap existing capabilities) ----------

async def _tool_web_search(query: str, max_sources: int = 5) -> dict:
    """Search web qua Gemini grounding."""
    from src.core.web_search import google_search
    result = await google_search(query, max_sources=max_sources)
    return {
        "summary": result.summary,
        "sources_count": len(result.sources),
        "top_sources": [s.title for s in result.sources[:3]],
    }


async def _tool_analyze_url(url: str) -> dict:
    """Phân tích URL (PDF/image/HTML) → blocks. Reuse logic từ /analyze-url."""
    import httpx
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/analyze-url",
            json={"url": url},
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "document_id": body.get("document_id"),
            "filename": body["document_metadata"]["filename"],
            "blocks_count": len(body.get("content_blocks", [])),
        }


async def _tool_library_load(slug: str) -> dict:
    """Load 1 sample từ library (physics, calculus, ...)."""
    import httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/library/{slug}/analyze",
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "document_id": body.get("document_id"),
            "filename": body["document_metadata"]["filename"],
            "blocks_count": len(body.get("content_blocks", [])),
        }


async def _tool_load_mock() -> dict:
    """Load mock newton dataset (13 blocks demo)."""
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BACKEND_URL}/api/v1/mock/analyze")
        resp.raise_for_status()
        body = resp.json()
        return {
            "document_id": body.get("document_id"),
            "filename": body["document_metadata"]["filename"],
            "blocks_count": len(body.get("content_blocks", [])),
        }


# ---------- Registry ----------

TOOLS: dict[str, ToolSpec] = {
    "web_search": ToolSpec(
        name="web_search",
        description=(
            "Tìm kiếm trên Google qua Gemini. "
            "Dùng khi user cần tìm thông tin/bài tập/tài liệu trên mạng."
        ),
        args_hint='{"query": "từ khoá tiếng Việt", "max_sources": 5}',
        handler=_tool_web_search,
    ),
    "analyze_url": ToolSpec(
        name="analyze_url",
        description=(
            "Phân tích nội dung từ URL (PDF, ảnh, hoặc bài viết web học liệu). "
            "Sau khi xong, document được index để user có thể hỏi chi tiết."
        ),
        args_hint='{"url": "https://example.com/article"}',
        handler=_tool_analyze_url,
    ),
    "library_load": ToolSpec(
        name="library_load",
        description=(
            "Tải 1 trong 6 sample sẵn có: physics, calculus, linear_algebra, "
            "chemistry, statistics, wave_physics."
        ),
        args_hint='{"slug": "physics"}',
        handler=_tool_library_load,
    ),
    "load_mock": ToolSpec(
        name="load_mock",
        description="Load mock data Định luật Newton (13 blocks demo). Dùng khi user nói 'tài liệu mẫu'.",
        args_hint='{}',
        handler=_tool_load_mock,
    ),
}


def list_tool_descriptions() -> str:
    """Format toàn bộ tools cho planner system prompt."""
    lines = []
    for tool in TOOLS.values():
        lines.append(f"- {tool.name}: {tool.description}\n  Args: {tool.args_hint}")
    return "\n".join(lines)


async def run_tool(name: str, args: dict[str, Any]) -> Any:
    """Gọi 1 tool với args, return result."""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    spec = TOOLS[name]
    logger.info(f"[tools] run {name} args={args}")
    return await spec.handler(**args)
