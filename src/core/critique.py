"""
VisionarySTEM Critique Engine — Sprint 8.2
============================================
Second-pass review to flag potential hallucinations from primary analysis.
Pattern from research/findings/13-multiagent-edu.md (MA-LED Belief Construction).

Cost: ~1x extra Gemini call. Default: only run for tier="pro".
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field

from src.api.schemas import ContentBlock
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


CRITIQUE_PROMPT_TEMPLATE = """Bạn là chuyên gia review nội dung STEM cho người khiếm thị.

Dưới đây là {n_blocks} block đã phân tích từ tài liệu STEM. Với mỗi block, đánh giá lại:

(a) **LaTeX validity** — nếu block.type == "math": LaTeX có hợp lệ và đúng nội dung không?
(b) **Spoken text accuracy** — spoken_text có đúng nghĩa toán/khoa học, đúng thuật ngữ tiếng Việt?
(c) **Type consistency** — type có khớp với raw_content không?
(d) **Missing important info** — có thông tin quan trọng bị bỏ sót không?

Trả về JSON list. Với mỗi block:
- `block_id`: id của block
- `critique_score`: 0.0 đến 1.0 (1.0 = hoàn hảo, < 0.7 = đáng nghi)
- `issues`: danh sách vấn đề tìm thấy bằng tiếng Việt (rỗng nếu không có)

Block để review:
{blocks_json}
"""


class BlockCritique(BaseModel):
    block_id: str
    critique_score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    critiques: list[BlockCritique]


class CritiqueEngine:
    """Second-pass review engine."""

    REVIEW_THRESHOLD = 0.7
    GEMINI_WEIGHT = 0.6
    CRITIQUE_WEIGHT = 0.4

    def __init__(self):
        self._cache: dict[str, list[BlockCritique]] = {}

    def critique_blocks(self, document_id: str, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """
        Run critique pass; return blocks with critique_score, needs_review, critique_issues set.
        Caches by document_id to avoid re-running.
        """
        if not blocks:
            return blocks

        if document_id in self._cache:
            return self._merge_into_blocks(blocks, self._cache[document_id])

        # Build prompt with compact block JSON (only critical fields, save tokens)
        compact = [
            {
                "id": b.id,
                "type": b.type,
                "raw_content": b.raw_content[:200],
                "latex": b.latex,
                "spoken_text": b.spoken_text[:200],
                "confidence": round(b.confidence, 2),
            }
            for b in blocks
        ]
        prompt = CRITIQUE_PROMPT_TEMPLATE.format(
            n_blocks=len(blocks),
            blocks_json=json.dumps(compact, ensure_ascii=False, indent=1),
        )

        engine = get_engine()
        try:
            response = engine.client.models.generate_content(
                model=engine.model,
                contents=[types.Part(text=prompt)],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CritiqueResult,
                    temperature=0.1,
                ),
            )
            result: CritiqueResult = response.parsed
            if result is None:
                try:
                    result = CritiqueResult(**json.loads(response.text))
                except Exception as e:
                    logger.error(f"Failed to parse critique: {e}")
                    return blocks  # graceful degradation
        except Exception as e:
            logger.error(f"Critique pass failed: {e}", exc_info=True)
            return blocks

        self._cache[document_id] = result.critiques
        return self._merge_into_blocks(blocks, result.critiques)

    def _merge_into_blocks(
        self,
        blocks: list[ContentBlock],
        critiques: list[BlockCritique],
    ) -> list[ContentBlock]:
        crit_by_id = {c.block_id: c for c in critiques}
        for b in blocks:
            crit = crit_by_id.get(b.id)
            if crit is None:
                continue
            b.critique_score = crit.critique_score
            b.critique_issues = list(crit.issues) if crit.issues else None
            b.needs_review = crit.critique_score < self.REVIEW_THRESHOLD
            # Merge confidence: weighted average
            b.confidence = round(
                self.GEMINI_WEIGHT * b.confidence + self.CRITIQUE_WEIGHT * crit.critique_score,
                3,
            )
        return blocks


# Singleton
_critique: Optional[CritiqueEngine] = None


def get_critique() -> CritiqueEngine:
    global _critique
    if _critique is None:
        _critique = CritiqueEngine()
    return _critique
