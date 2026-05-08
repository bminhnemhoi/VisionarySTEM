"""
Planner — convert user request thành Plan có nhiều steps.

Dùng Gemini structured output. KHÔNG chain args giữa steps trong MVP này.
Mỗi step độc lập, args đã đầy đủ từ planner.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field

from src.agents.tools import list_tool_descriptions
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    tool: str = Field(description="Tên tool, phải trong list available tools")
    # NOTE: args là JSON string (không phải dict) vì Gemini schema không support
    # dict[str, Any] với additionalProperties=True. Parse JSON ở executor.
    args_json: str = Field(
        default="{}",
        description='JSON object string với args cho tool. VD: {"query": "abc"} hoặc {}',
    )
    narration: str = Field(description="Thông báo tiếng Việt khi step bắt đầu (10-20 từ)")

    def get_args(self) -> dict[str, Any]:
        """Parse args_json safely → dict."""
        try:
            args = json.loads(self.args_json) if self.args_json else {}
            return args if isinstance(args, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}


class Plan(BaseModel):
    steps: list[PlanStep] = Field(description="Danh sách steps tuần tự")
    summary_narration: str = Field(
        description="Câu tổng kết tiếng Việt khi tất cả steps xong (15-30 từ)"
    )
    plan_overview: str = Field(
        description="Mô tả ngắn về plan để AI nói TRƯỚC khi chạy (15-30 từ)"
    )


def _build_system_prompt() -> str:
    return f"""Bạn là planner cho VisionarySTEM — AI assistant tiếng Việt cho sinh viên khiếm thị.

NHIỆM VỤ:
Phân tích yêu cầu user → output 1 PLAN có 1-4 steps tuần tự, dùng các tool có sẵn.

TOOLS AVAILABLE:
{list_tool_descriptions()}

QUY TẮC:
1. Mỗi step phải dùng đúng 1 tool trong list trên (KHÔNG sáng chế tool mới).
2. `args_json`: JSON STRING — đặt args trong dấu ngoặc kép escape đúng. Ví dụ: "{{\\"query\\": \\"abc\\"}}".
   Nếu tool không cần args → "{{}}".
3. Tools độc lập — KHÔNG dùng output của step trước (chưa support chaining).
4. narration mỗi step: tiếng Việt natural, 10-20 từ, nói rõ đang làm gì.
   Ví dụ: "Tôi tìm bài tập chất béo trên mạng" / "Tôi tải tài liệu Vật lý Newton"
5. plan_overview: 1 câu nói TRƯỚC khi chạy. Liệt kê các việc sẽ làm.
   Ví dụ: "Tôi sẽ làm 2 việc: tìm bài tập chất béo trên mạng, sau đó tải tài liệu vật lý."
6. summary_narration: 1 câu nói SAU khi xong tất cả. Tổng kết kết quả + suggest next.
   Ví dụ: "Đã làm xong cả hai việc. Bạn muốn nghe tóm tắt cái nào trước?"

ƯỚC LƯỢNG SỐ STEPS:
- 1-2 step: thường gặp (1 search hoặc 1 load)
- 3-4 step: phức tạp (search nhiều topic, load nhiều sample)
- KHÔNG vượt 4 step (UX nặng nề).

TRƯỜNG HỢP MƠ HỒ:
- Nếu user yêu cầu KHÔNG rõ → output 1 step duy nhất với tool web_search và query là cả utterance.

VÍ DỤ CHUYỂN ĐỔI (lưu ý args_json là STRING):
- "tìm bài tập chất béo và bài tập đại số" →
  steps: [
    {{ tool: "web_search", args_json: "{{\\"query\\": \\"bài tập chất béo hoá 12\\"}}", narration: "Tôi tìm bài tập chất béo trên mạng" }},
    {{ tool: "web_search", args_json: "{{\\"query\\": \\"bài tập đại số tuyến tính\\"}}", narration: "Tôi tìm bài tập đại số tuyến tính" }}
  ]

- "thư viện vật lý và tài liệu mẫu" →
  steps: [
    {{ tool: "library_load", args_json: "{{\\"slug\\": \\"physics\\"}}", narration: "Tôi tải sách Vật lý định luật Newton" }},
    {{ tool: "load_mock", args_json: "{{}}", narration: "Tôi tải tài liệu mẫu Newton" }}
  ]
"""


async def make_plan(user_request: str) -> Plan:
    """Convert user request → Plan có 1-4 steps."""
    if not user_request or not user_request.strip():
        raise ValueError("user_request rỗng")

    engine = get_engine()
    response = engine.client.models.generate_content(
        model=engine.model,
        contents=user_request,
        config=types.GenerateContentConfig(
            system_instruction=_build_system_prompt(),
            response_mime_type="application/json",
            response_schema=Plan,
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    plan = response.parsed
    if plan is None:
        try:
            plan = Plan(**json.loads(response.text))
        except Exception as e:
            raise RuntimeError(f"Failed to parse plan: {e}")

    # Validate: tools đều phải có trong registry
    from src.agents.tools import TOOLS
    valid_steps = []
    for step in plan.steps:
        if step.tool in TOOLS:
            valid_steps.append(step)
        else:
            logger.warning(f"[planner] dropped invalid tool '{step.tool}'")
    plan.steps = valid_steps[:4]  # cap ở 4 step

    logger.info(
        f"[planner] {user_request!r} → {len(plan.steps)} steps: "
        f"{[s.tool for s in plan.steps]}"
    )
    return plan
