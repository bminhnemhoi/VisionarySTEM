# Multi-agent LLM cho Giáo dục (AutoGen, CrewAI, MA-LED)

## TL;DR
- **Multi-agent** = nhiều LLM "vai trò" khác nhau hợp tác. Cho VisionarySTEM: **Tutor agent** + **Critique agent** + **Pedagogy agent**.
- **AutoGen** (Microsoft) — framework chính, được dùng nhiều trong production research.
- **CrewAI** — orchestration đơn giản hơn, role-based.
- **LangGraph** — stateful agent flows.
- **MA-LED** (paper user đang làm) — Belief Construction Layer + Dempster-Shafer fusion → áp dụng cho confidence merging.

## 3 patterns multi-agent áp dụng được

### Pattern A: Tutor + Critique + Pedagogue (Sprint 8 áp dụng)
```
User question
    ↓
[Tutor agent]  — generate raw answer
    ↓
[Critique agent] — fact-check, flag errors
    ↓
[Pedagogue agent] — rewrite for blind learner: shorter sentences, more examples
    ↓
Final answer to user
```
- Cost: ~3x token mỗi turn → chỉ enable cho `tier="pro"`
- Latency: +2-3s nhưng accuracy +15-25%

### Pattern B: Belief Fusion (MA-LED style)
Có 3 agent vote về `confidence` của mỗi block:
- Agent 1 (visual): "block này có rõ không?"
- Agent 2 (semantic): "spoken_text có đúng nghĩa toán không?"
- Agent 3 (consistency): "có khớp với block xung quanh không?"

Dùng **Dempster-Shafer combination rule** thay vì averaging → handle conflict tốt hơn.

Reference: D:/hoinghi_IUKM2026/paper/main_v4.tex `BCL` (Belief Construction Layer).

### Pattern C: Conversation Turn-taking (AutoGen GroupChat)
Cho `/chat` endpoint phức tạp:
- User → moderator → routes to subject expert (math/physics/chemistry tutor)
- Mỗi expert có vocabulary + examples chuyên biệt
- Moderator decide khi nào "wrap up" (user hết hỏi follow-up)

## Khung implementation cho Sprint 8

### Cách 1 — Direct Gemini calls (simplest, recommended cho Sprint 8 MVP)
Không cần framework heavy. Chỉ làm 2 sequential Gemini calls:
```python
async def tutor_with_critique(question, context):
    raw = await gemini.generate("You are tutor. Q: " + question)
    critiqued = await gemini.generate(f"Review this answer for errors: {raw}")
    return critiqued
```

### Cách 2 — LangGraph (stateful)
Khi cần state machine phức tạp (Sprint 6+):
```python
from langgraph.graph import StateGraph

graph = StateGraph(ChatState)
graph.add_node("tutor", tutor_fn)
graph.add_node("critique", critique_fn)
graph.add_node("pedagogue", pedagogue_fn)
graph.add_edge("tutor", "critique")
graph.add_edge("critique", "pedagogue")
graph.set_entry_point("tutor")
graph.set_finish_point("pedagogue")
```

### Cách 3 — AutoGen GroupChat (advanced)
Cho enterprise tier sau:
```python
from autogen import GroupChat, GroupChatManager
agents = [tutor, critique, pedagogue]
group = GroupChat(agents=agents, messages=[], max_round=10)
manager = GroupChatManager(groupchat=group, llm_config=...)
```

## So sánh framework

| Framework | Pros | Cons | Khi nào dùng |
|-----------|------|------|--------------|
| **Direct Gemini** (no framework) | Đơn giản, ít abstraction | Code lặp khi nhiều agents | Sprint 8 MVP |
| **LangGraph** | State machine clean, debuggable | Learning curve | Sprint 6+ pedagogy flows |
| **AutoGen** (Microsoft) | Production-grade, GroupChat | Heavy, opinionated | Enterprise tier sau |
| **CrewAI** | Role-based, dễ đọc | Newer, ít examples | Workshop/demo |
| **LangChain** | Phổ biến | Bloated, thay đổi nhiều | Tránh nếu được |

## MA-LED methodology (user's own paper) cho VisionarySTEM

Từ `D:/hoinghi_IUKM2026/paper/main_v4.tex`, áp dụng:
- **Belief Construction Layer (BCL)**: mỗi agent output không phải xác suất 1-D mà là **belief mass distribution** trên Frame of Discernment {correct, incorrect, unknown}
- **Dempster-Shafer combination**: fuse 2-3 belief từ Tutor + Critique + Pedagogy → final confidence
- **Risk-coverage curve** (RC) cho selective prediction: chỉ trả lời khi confidence ≥ threshold; còn lại "Tôi không chắc, bạn có thể hỏi giáo viên không?"

Đây là **đóng góp khoa học** rõ rệt — kết nối research paper user đang viết với product. Có thể publish co-paper "MA-LED for Accessible STEM Tutoring" tại ASSETS hoặc CHI.

## Tools đã clone
- `research/tools/autogen` — Microsoft AutoGen
- `research/tools/crewai` — CrewAI
- `research/tools/langgraph` — LangGraph

## Tham chiếu
- AutoGen paper: arXiv 2308.08155
- CrewAI: github.com/joaomdmoura/crewAI
- LangGraph: github.com/langchain-ai/langgraph
- MA-LED: D:/hoinghi_IUKM2026/paper/main_v4.tex
- "Tutoring with LLMs: Recent Advances" NAACL 2025
- Dempster-Shafer review: Yager & Liu 2008
