"""
VisionarySTEM - API Schemas (Pydantic Models)
===============================================
Defines the JSON contract between Person A (Backend) and Person B (Frontend).
This is the SINGLE SOURCE OF TRUTH for data structures.

Định nghĩa hợp đồng JSON giữa Người A (Backend) và Người B (Frontend).
Đây là NGUỒN DỮ LIỆU DUY NHẤT cho cấu trúc dữ liệu.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """
    Spatial coordinates of a content block on the page.
    All values are percentages (0-100) relative to page dimensions.
    
    Tọa độ không gian của một khối nội dung trên trang.
    Tất cả giá trị là phần trăm (0-100) so với kích thước trang.
    """
    page: int = Field(description="Page number (1-indexed) / Số trang (bắt đầu từ 1)")
    x: float = Field(ge=0, le=100, description="Distance from left edge (%) / Khoảng cách từ cạnh trái (%)")
    y: float = Field(ge=0, le=100, description="Distance from top edge (%) / Khoảng cách từ cạnh trên (%)")
    w: float = Field(ge=0, le=100, description="Width of the block (%) / Chiều rộng khối (%)")
    h: float = Field(ge=0, le=100, description="Height of the block (%) / Chiều cao khối (%)")
    region: str = Field(description="Spatial region: top-left, center, bottom-right, etc. / Vùng không gian")


class ContentBlock(BaseModel):
    """
    A single content block extracted from the document.
    Một khối nội dung đơn lẻ được trích xuất từ tài liệu.

    Sprint 4: extended fields for accessibility export (EPUB3, MathML, Braille)
    and reading-order semantics. All extension fields are Optional for backward compat.
    """
    id: str = Field(description="Unique block ID (e.g., block_001) / Mã khối duy nhất")
    type: Literal["text", "math", "chart", "table", "figure"] = Field(
        description="Content type / Loại nội dung"
    )
    raw_content: str = Field(description="Original content as extracted / Nội dung gốc được trích xuất")
    latex: Optional[str] = Field(
        default=None,
        description="LaTeX representation (for math blocks) / Biểu diễn LaTeX (cho khối toán)"
    )
    spoken_text: str = Field(
        description="Natural Vietnamese speech text / Văn bản đọc tiếng Việt tự nhiên"
    )
    language: str = Field(default="vi", description="Language code / Mã ngôn ngữ")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="AI confidence score (0.0-1.0) / Điểm tin cậy của AI"
    )
    coordinates: Coordinates = Field(description="Spatial position on page / Vị trí không gian trên trang")

    # ============ Sprint 4 Accessibility Extensions ============
    reading_order: Optional[int] = Field(
        default=None,
        description="Linear reading order (1-indexed) — critical for screen readers when y/x ordering fails (multi-column, footnotes). / Thứ tự đọc tuyến tính.",
    )
    importance: Optional[Literal["primary", "secondary", "decorative"]] = Field(
        default=None,
        description="Content importance — lets users skip decorative elements. / Mức quan trọng.",
    )
    alt_text_long: Optional[str] = Field(
        default=None,
        description="Long descriptive alt text for figures/charts (WCAG longdesc equivalent). / Mô tả dài cho hình/biểu đồ.",
    )
    mathml: Optional[str] = Field(
        default=None,
        description="MathML representation (alternative to LaTeX for screen readers + Braille). / MathML thay thế.",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Parent block ID (for table cells, footnote refs, sub-figures). / Block cha.",
    )
    aria_role: Optional[str] = Field(
        default=None,
        description="ARIA role hint (math, figure, table, region, ...). / Gợi ý ARIA role.",
    )

    # ============ Sprint 8.2 Critique loop ============
    critique_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Critique agent score (0-1). Lower = more concerns. / Điểm critique từ agent thứ 2.",
    )
    needs_review: Optional[bool] = Field(
        default=None,
        description="Flag set when critique_score < threshold. / Cần xem lại do nghi vấn.",
    )
    critique_issues: Optional[list[str]] = Field(
        default=None,
        description="List of issues flagged by critique agent. / Danh sách vấn đề được cảnh báo.",
    )

    # ============ Sprint 8.3 Sonification ============
    sonification_data: Optional[dict] = Field(
        default=None,
        description="Extracted chart data points for sonification: {x_label, y_label, points: [[x,y]]}.",
    )


class SpatialIndex(BaseModel):
    """
    Mapping from spatial regions to block IDs for quick spatial queries.
    Ánh xạ từ vùng không gian đến mã khối để truy vấn không gian nhanh.
    """
    regions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Region name -> list of block IDs / Tên vùng -> danh sách mã khối"
    )


class DocumentMetadata(BaseModel):
    """
    Metadata about the processed document.
    Siêu dữ liệu về tài liệu đã xử lý.
    """
    filename: str = Field(description="Original filename / Tên file gốc")
    total_pages: int = Field(ge=1, description="Total pages processed / Tổng số trang đã xử lý")
    processing_time_ms: int = Field(ge=0, description="Processing time in milliseconds / Thời gian xử lý (ms)")
    model_used: str = Field(description="AI model used / Model AI đã sử dụng")


class DocumentAnalysisResponse(BaseModel):
    """
    Complete response from the /analyze endpoint.
    This is the main JSON contract between Person A and Person B.
    
    Phản hồi đầy đủ từ endpoint /analyze.
    Đây là hợp đồng JSON chính giữa Người A và Người B.
    """
    document_metadata: DocumentMetadata
    content_blocks: list[ContentBlock]
    spatial_index: SpatialIndex


class SpatialQueryRequest(BaseModel):
    """
    Request body for spatial voice queries.
    Body yêu cầu cho truy vấn giọng nói không gian.
    """
    query: str = Field(description="User's voice query text / Văn bản truy vấn giọng nói của người dùng")
    document_id: Optional[str] = Field(
        default=None,
        description="ID of previously analyzed document / ID tài liệu đã phân tích trước đó"
    )


class SpatialQueryResponse(BaseModel):
    """
    Response for spatial queries.
    Phản hồi cho truy vấn không gian.
    """
    query: str
    matched_blocks: list[ContentBlock]
    spoken_answer: str = Field(description="Natural Vietnamese answer / Câu trả lời tiếng Việt tự nhiên")


class HealthResponse(BaseModel):
    """Health check response / Phản hồi kiểm tra sức khỏe"""
    status: str = "ok"
    service: str = "VisionarySTEM API"
    version: str = "1.0.0"
    gemini_model: str = ""


class ErrorResponse(BaseModel):
    """Error response / Phản hồi lỗi"""
    error: str
    detail: Optional[str] = None


# ============================================================
# Sprint 8.1 — Tutor chat
# ============================================================

class ChatMessage(BaseModel):
    """One message in a tutor conversation."""
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: Optional[str] = None
    cited_blocks: Optional[list[str]] = Field(
        default=None,
        description="Block IDs referenced by this message (assistant only).",
    )


class ChatRequest(BaseModel):
    """User message to tutor."""
    document_id: str = Field(description="Previously analyzed document ID")
    session_id: str = Field(description="Conversation session ID (uuid)")
    message: str = Field(min_length=1, description="User question in Vietnamese")
    voice_mode: bool = Field(default=False, description="If true, optimize reply for TTS (shorter sentences)")


class ChatResponse(BaseModel):
    """Tutor reply with follow-up suggestions."""
    reply_text: str
    suggested_followups: list[str] = Field(
        default_factory=list,
        description="2-3 suggested next questions in Vietnamese.",
    )
    cited_blocks: list[str] = Field(
        default_factory=list,
        description="Block IDs the reply references.",
    )
    session_id: str


# ============================================================
# Sprint 8.4 — Camera snapshot
# ============================================================

class CameraSnapshotResponse(BaseModel):
    """Quick analysis of a camera frame (board/slide)."""
    spoken_text: str = Field(description="Vietnamese description of the frame, ≤3 sentences.")
    raw_content: str = Field(description="Raw extracted text/formulas")
    confidence: float = Field(ge=0.0, le=1.0)
    has_math: bool = False
    has_chart: bool = False
