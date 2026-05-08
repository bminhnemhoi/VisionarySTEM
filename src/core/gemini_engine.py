"""
VisionarySTEM - Gemini 2.5 Flash Engine
========================================
Core AI engine that uses Gemini 2.5 Flash's native multimodal capabilities
to analyze STEM documents (PDFs/Images) and extract structured content.

Lõi AI sử dụng khả năng đa phương thức gốc của Gemini 2.5 Flash
để phân tích tài liệu STEM (PDF/Ảnh) và trích xuất nội dung có cấu trúc.
"""

import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.config import GEMINI_MODEL, GEMINI_SYSTEM_PROMPT, require_api_key

logger = logging.getLogger(__name__)

# ============================================
# Pydantic schema for Gemini structured output
# ============================================

class GeminiCoordinates(BaseModel):
    """Coordinates schema for Gemini response"""
    page: int = Field(description="Số trang (bắt đầu từ 1)")
    x: float = Field(description="Khoảng cách từ cạnh trái (%)")
    y: float = Field(description="Khoảng cách từ cạnh trên (%)")
    w: float = Field(description="Chiều rộng khối (%)")
    h: float = Field(description="Chiều cao khối (%)")
    region: str = Field(description="Vùng: top-left, top-center, top-right, center-left, center, center-right, bottom-left, bottom-center, bottom-right")


class GeminiContentBlock(BaseModel):
    """Single content block from Gemini analysis"""
    id: str = Field(description="Mã khối: block_001, block_002, ...")
    type: str = Field(description="Loại: text, math, chart, table, figure")
    raw_content: str = Field(description="Nội dung gốc được trích xuất")
    latex: Optional[str] = Field(default=None, description="Mã LaTeX (chỉ cho khối toán)")
    spoken_text: str = Field(description="Văn bản đọc tiếng Việt tự nhiên")
    confidence: float = Field(description="Điểm tin cậy 0.0 đến 1.0")
    coordinates: GeminiCoordinates


class GeminiAnalysisResult(BaseModel):
    """Complete analysis result from Gemini"""
    content_blocks: list[GeminiContentBlock]


# ============================================
# Gemini Engine Class
# ============================================

class GeminiEngine:
    """
    Wraps the Gemini 2.5 Flash API for STEM document analysis.
    Handles file upload, multimodal prompting, and structured JSON output.
    
    Bọc API Gemini 2.5 Flash cho phân tích tài liệu STEM.
    Xử lý upload file, prompt đa phương thức, và output JSON có cấu trúc.
    """

    def __init__(self):
        """Initialize the Gemini client with API key."""
        self.client = genai.Client(api_key=require_api_key())
        self.model = GEMINI_MODEL
        logger.info(f"✅ GeminiEngine initialized with model: {self.model}")

    def analyze_image_bytes(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        page_number: int = 1,
    ) -> GeminiAnalysisResult:
        """
        Analyze an image from bytes (for inline image analysis without file upload).
        Useful for extracting individual pages from PDFs as images.
        
        Phân tích ảnh từ bytes (phân tích ảnh nội tuyến không cần upload file).
        Hữu ích để trích xuất từng trang PDF dưới dạng ảnh.
        """
        analysis_prompt = f"""Phân tích trang tài liệu STEM này.

Trích xuất TẤT CẢ các khối nội dung bạn nhìn thấy.
Với mỗi khối, cung cấp id, type, raw_content, latex, spoken_text, confidence, và coordinates.

Công thức toán PHẢI được đọc bằng tiếng Việt tự nhiên.
Tọa độ page = {page_number}."""

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                image_part,
                analysis_prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=GeminiAnalysisResult,
                temperature=0.1,
            ),
        )

        result = response.parsed
        if result is None:
            try:
                raw_json = json.loads(response.text)
                result = GeminiAnalysisResult(**raw_json)
            except Exception as e:
                raise RuntimeError(f"Failed to parse Gemini response: {e}")

        return result


# ============================================
# Module-level convenience function
# ============================================

_engine: Optional[GeminiEngine] = None

def get_engine() -> GeminiEngine:
    """
    Get or create a singleton GeminiEngine instance.
    Lấy hoặc tạo một instance GeminiEngine duy nhất.
    """
    global _engine
    if _engine is None:
        _engine = GeminiEngine()
    return _engine
