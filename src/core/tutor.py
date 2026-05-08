"""
VisionarySTEM Tutor Engine — Sprint 8.1
========================================
Multi-turn conversation about an analyzed document.
Pattern from research/findings/11-tutor-ai-accessibility.md.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from google.genai import types
from pydantic import BaseModel, Field

from src.api.schemas import ChatMessage, ChatResponse, DocumentAnalysisResponse
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


TUTOR_SYSTEM_PROMPT_TEMPLATE = """Bạn là gia sư STEM tiếng Việt cho sinh viên khiếm thị Việt Nam.

Đã phân tích tài liệu: {filename} ({total_pages} trang, {n_blocks} block).

Tóm tắt nội dung tài liệu:
{block_summaries}

QUY TẮC TRẢ LỜI BẮT BUỘC:

1. Trả lời 100% bằng tiếng Việt tự nhiên — KHÔNG đọc công thức kiểu tiếng Anh.
   ❌ Sai: "F equals m a"
   ✅ Đúng: "Lực bằng khối lượng nhân gia tốc"

2. ĐỘ DÀI CÂU TRẢ LỜI:
   - **Mỗi câu** ngắn (tối đa 25 từ) cho dễ nghe TTS.
   - **TỔNG câu trả lời PHẢI ĐẦY ĐỦ và có chiều sâu** — trung bình 4-7 câu, có giải thích rõ ràng + ví dụ cụ thể.
   - ❌ TUYỆT ĐỐI KHÔNG cụt ngủn kiểu "Tôi có thể giải thích..." rồi dừng.
   - ❌ KHÔNG được trả lời chung chung "Tôi giúp bạn hiểu tài liệu."
   - ✅ Phải nói RÕ + CỤ THỂ. Ví dụ khi user hỏi "bạn làm được gì":
     "Tài liệu này có {n_blocks} phần, trải dài {total_pages} trang. Tôi có thể đọc lại từng phần — ví dụ phần đầu là tiêu đề chương về ba định luật Newton. Tôi có thể giải thích đơn giản hơn các công thức như định luật hai. Tôi cho ví dụ thực tế đời sống. Tôi tóm tắt cả tài liệu trong vài câu. Bạn muốn nghe phần nào trước, hay muốn tôi tóm tắt?"

3. CHO VÍ DỤ CỤ THỂ — đặc biệt là đời sống Việt Nam khi giải thích khái niệm.
   Ví dụ: "Lực ma sát là khi bạn đẩy chiếc bàn — sàn đẩy ngược lại bạn".

4. ❌❌❌ TUYỆT ĐỐI KHÔNG ĐỌC ID KỸ THUẬT cho user nghe! User là sinh viên khiếm thị, nghe "block không không hai" hoàn toàn vô nghĩa với họ.
   ❌ SAI: "Bạn có thể nghe block_005 để hiểu công thức"
   ❌ SAI: "Trong block_002 có nói về..."
   ✅ ĐÚNG: Diễn đạt theo MIÊU TẢ NỘI DUNG / VỊ TRÍ tự nhiên:
      - "phần đầu / phần mở đầu / tiêu đề chương"
      - "phần giới thiệu định luật một"
      - "công thức F bằng m a"
      - "đoạn ví dụ thực tế về tên lửa"
      - "biểu đồ lực và gia tốc"
      - "bài tập cuối"
   Cụ thể với tài liệu này:
{block_summaries}
   Khi user nói "đọc lại phần giới thiệu" / "phần định luật một" / "ví dụ" → bạn HIỂU và đề xuất ID block tương ứng qua field `cited_blocks` (cho frontend), nhưng văn bản nói KHÔNG được đọc ID.

5. ❌ KHÔNG dùng markdown bullet (*, -) hay heading (#) — TTS đọc thô tiếng "sao", "thăng".
   Thay bằng "Thứ nhất", "Thứ hai", "Một là", "Hai là", "Đầu tiên".

6. KHÔNG dùng emoji, ký hiệu đặc biệt — TTS đọc không tự nhiên.

7. Nếu user hỏi ngoài phạm vi tài liệu, lịch sự: "Tài liệu này không đề cập tới X. Bạn có muốn tôi giải thích từ kiến thức chung không?".

8. Cuối câu trả lời, gợi ý 1-2 câu hỏi follow-up tự nhiên (qua field `suggested_followups`).
   `cited_blocks`: TRẢ về đúng ID kỹ thuật của các block liên quan (cho frontend xử lý), KHÔNG đọc trong reply_text.
"""


class GeminiChatReply(BaseModel):
    """Structured Gemini output."""
    reply_text: str = Field(description="Câu trả lời cho user, đã chuẩn bị cho TTS")
    cited_blocks: list[str] = Field(
        default_factory=list,
        description="Danh sách block ID được trích dẫn (vd: block_002, block_005)",
    )
    suggested_followups: list[str] = Field(
        default_factory=list,
        description="2-3 câu hỏi follow-up gợi ý",
    )


class TutorEngine:
    """
    Multi-turn tutor over a previously-analyzed document.

    Sessions stored in memory keyed by session_id. Sprint 5 will persist to DB.
    """

    def __init__(self):
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._documents: dict[str, DocumentAnalysisResponse] = {}

    # ----------------- Session API -----------------

    def new_session(self) -> str:
        sid = uuid.uuid4().hex
        self._sessions[sid] = []
        return sid

    def register_document(self, document_id: str, response: DocumentAnalysisResponse) -> None:
        """Cache the analysis so the tutor can reference its blocks."""
        self._documents[document_id] = response

    def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._sessions.get(session_id, []))

    def reset_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    # ----------------- Build prompt context -----------------

    def _build_block_summaries(self, doc: DocumentAnalysisResponse, max_blocks: int = 30) -> str:
        """One-line summary per block for the system prompt."""
        lines = []
        for b in doc.content_blocks[:max_blocks]:
            latex_part = f" | LaTeX: {b.latex}" if b.latex else ""
            lines.append(
                f"- {b.id} [{b.type} @ {b.coordinates.region}, page {b.coordinates.page}]: "
                f"{b.spoken_text[:120]}{latex_part}"
            )
        if len(doc.content_blocks) > max_blocks:
            lines.append(f"... (+{len(doc.content_blocks) - max_blocks} block khác)")
        return "\n".join(lines)

    def _system_prompt(self, doc: DocumentAnalysisResponse) -> str:
        return TUTOR_SYSTEM_PROMPT_TEMPLATE.format(
            filename=doc.document_metadata.filename,
            total_pages=doc.document_metadata.total_pages,
            n_blocks=len(doc.content_blocks),
            block_summaries=self._build_block_summaries(doc),
        )

    # ----------------- Main chat -----------------

    def chat(
        self,
        document_id: str,
        session_id: str,
        user_message: str,
        voice_mode: bool = False,
    ) -> ChatResponse:
        """Send a user message, return tutor reply."""
        doc = self._documents.get(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not registered with tutor")

        # Initialize session if new
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        history = self._sessions[session_id]
        now = datetime.now(timezone.utc).isoformat()

        # Append user turn
        history.append(ChatMessage(role="user", content=user_message, timestamp=now))

        # Build Gemini contents: system + previous turns + new user message
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        engine = get_engine()
        try:
            response = engine.client.models.generate_content(
                model=engine.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self._system_prompt(doc),
                    response_mime_type="application/json",
                    response_schema=GeminiChatReply,
                    temperature=0.4 if voice_mode else 0.5,
                    max_output_tokens=1500 if voice_mode else 2400,
                ),
            )
            reply: GeminiChatReply = response.parsed
            if reply is None:
                # Fallback parse
                try:
                    reply = GeminiChatReply(**json.loads(response.text))
                except Exception as e:
                    logger.error(f"Failed to parse tutor reply: {e}")
                    reply = GeminiChatReply(
                        reply_text="Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi. Bạn thử hỏi lại nhé?",
                        cited_blocks=[],
                        suggested_followups=[],
                    )
        except Exception as e:
            logger.error(f"Gemini chat failed: {e}", exc_info=True)
            reply = GeminiChatReply(
                reply_text=f"Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại.",
                cited_blocks=[],
                suggested_followups=[],
            )

        # Validate cited_blocks — only keep ones that actually exist in the document
        valid_block_ids = {b.id for b in doc.content_blocks}
        reply.cited_blocks = [bid for bid in reply.cited_blocks if bid in valid_block_ids]

        # Append assistant turn
        history.append(ChatMessage(
            role="assistant",
            content=reply.reply_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cited_blocks=reply.cited_blocks,
        ))

        return ChatResponse(
            reply_text=reply.reply_text,
            suggested_followups=reply.suggested_followups[:3],
            cited_blocks=reply.cited_blocks,
            session_id=session_id,
        )

    # ----------------- Streaming chat -----------------

    async def chat_stream(
        self,
        document_id: str,
        session_id: str,
        user_message: str,
        focus_block_id: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """
        Stream the assistant reply token-by-token (SSE-friendly).

        Yields events:
          - {"event": "token", "data": {"text": "..."}}        — partial text
          - {"event": "done",  "data": {"reply_text": "...", "cited_blocks": [...]}}
          - {"event": "error", "data": {"detail": "..."}}

        Use a simpler text-only format (no JSON schema) so streaming is natural.
        """
        import asyncio

        doc = self._documents.get(document_id)
        if not doc:
            yield {"event": "error", "data": {"detail": f"Document {document_id} not registered"}}
            return

        if session_id not in self._sessions:
            self._sessions[session_id] = []
        history = self._sessions[session_id]
        now = datetime.now(timezone.utc).isoformat()

        # Optional focus_block: prepend hint to user message
        prefix = ""
        if focus_block_id:
            for b in doc.content_blocks:
                if b.id == focus_block_id:
                    prefix = (
                        f"[Người dùng đang nghe block {b.id} ({b.type}): "
                        f"\"{b.spoken_text[:200]}\"] "
                    )
                    break

        full_user_msg = prefix + user_message
        history.append(ChatMessage(role="user", content=full_user_msg, timestamp=now))

        # Build conversation contents
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        engine = get_engine()
        accumulated = ""
        try:
            # Run streaming sync call in thread to keep loop alive
            def _stream_sync():
                return engine.client.models.generate_content_stream(
                    model=engine.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self._system_prompt(doc),
                        temperature=0.5,
                        max_output_tokens=2048,
                    ),
                )

            # Simple wrapper: collect all chunks in thread, yield as tokens here
            chunks: list[str] = []

            def _collect():
                for chunk in _stream_sync():
                    if chunk.text:
                        chunks.append(chunk.text)

            # Run collection in thread, yield from main loop as chunks arrive
            loop = asyncio.get_event_loop()
            collect_task = loop.run_in_executor(None, _collect)

            already_yielded = 0
            while not collect_task.done() or already_yielded < len(chunks):
                if already_yielded < len(chunks):
                    new_text = chunks[already_yielded]
                    accumulated += new_text
                    already_yielded += 1
                    yield {"event": "token", "data": {"text": new_text, "accumulated": accumulated}}
                else:
                    await asyncio.sleep(0.05)

            await collect_task

            # Detect cited blocks from accumulated text (simple regex)
            valid_block_ids = {b.id for b in doc.content_blocks}
            cited = re.findall(r"\bblock_\d{3,}\b", accumulated)
            cited = [b for b in cited if b in valid_block_ids]
            cited = list(dict.fromkeys(cited))  # dedupe preserving order

            # Append assistant turn to history
            history.append(ChatMessage(
                role="assistant",
                content=accumulated,
                timestamp=datetime.now(timezone.utc).isoformat(),
                cited_blocks=cited,
            ))

            yield {
                "event": "done",
                "data": {
                    "reply_text": accumulated,
                    "cited_blocks": cited,
                    "session_id": session_id,
                },
            }
        except Exception as e:
            logger.error(f"Stream chat failed: {e}", exc_info=True)
            yield {"event": "error", "data": {"detail": str(e)}}


# Singleton
_tutor: Optional[TutorEngine] = None


def get_tutor() -> TutorEngine:
    global _tutor
    if _tutor is None:
        _tutor = TutorEngine()
    return _tutor
