"""
Executor — chạy Plan tuần tự, yield SSE events cho frontend.

Events emit:
- plan_ready: { plan_overview, steps_count }       — sau khi planner xong, trước execute
- step_start: { index, narration, tool }           — bắt đầu step
- step_done: { index, summary }                    — step xong (với summary ngắn)
- step_error: { index, error }                     — step lỗi (executor STOP)
- plan_done: { summary_narration, results }        — tất cả xong
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from src.agents.planner import Plan
from src.agents.tools import run_tool

logger = logging.getLogger(__name__)


def _summarize_result(tool: str, result: Any) -> str:
    """Tóm tắt result của 1 step thành 1 câu narration tiếng Việt cho TTS."""
    if not isinstance(result, dict):
        return f"Hoàn tất {tool}."
    if tool == "web_search":
        n = result.get("sources_count", 0)
        top = result.get("top_sources", [])
        if n > 0 and top:
            return (
                f"Tôi tìm được {n} nguồn. " + ", ".join(f"{i + 1}, {t}" for i, t in enumerate(top[:3]))
            )
        return "Tôi đã tìm xong."
    if tool in ("analyze_url", "library_load", "load_mock"):
        n = result.get("blocks_count", 0)
        fname = result.get("filename", "tài liệu")
        return f"Đã tải {fname}, có {n} phần."
    return f"Hoàn tất {tool}."


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def execute_plan_sse(plan: Plan) -> AsyncIterator[str]:
    """
    Async generator yield raw SSE strings.

    Frontend consume qua EventSource hoặc fetch + reader.
    """
    # 1. plan_ready — narrate overview trước khi chạy
    yield _format_sse(
        "plan_ready",
        {
            "plan_overview": plan.plan_overview,
            "steps_count": len(plan.steps),
            "steps": [{"tool": s.tool, "narration": s.narration} for s in plan.steps],
        },
    )

    if not plan.steps:
        yield _format_sse(
            "plan_done",
            {"summary_narration": "Tôi không có việc gì để làm. Bạn thử yêu cầu khác.", "results": []},
        )
        return

    # 2. Execute steps tuần tự
    results: list[dict] = []
    for i, step in enumerate(plan.steps):
        yield _format_sse(
            "step_start",
            {"index": i, "narration": step.narration, "tool": step.tool},
        )
        try:
            args = step.get_args()
            result = await run_tool(step.tool, args)
            summary = _summarize_result(step.tool, result)
            yield _format_sse(
                "step_done",
                {
                    "index": i,
                    "summary": summary,
                    "result_meta": result if isinstance(result, dict) else None,
                },
            )
            results.append(
                {"step": i, "tool": step.tool, "summary": summary, "meta": result}
            )
        except Exception as e:
            logger.error(f"[executor] step {i} ({step.tool}) failed: {e}", exc_info=True)
            yield _format_sse(
                "step_error",
                {"index": i, "tool": step.tool, "error": str(e)},
            )
            # Dừng plan khi gặp lỗi (Phase 4 sẽ thêm error recovery confirmation)
            yield _format_sse(
                "plan_done",
                {
                    "summary_narration": (
                        f"Xin lỗi, có lỗi ở bước {i + 1}. Đã dừng. Bạn thử yêu cầu khác nhé."
                    ),
                    "results": results,
                },
            )
            return

    # 3. plan_done — narrate summary
    yield _format_sse(
        "plan_done",
        {"summary_narration": plan.summary_narration, "results": results},
    )
