"""
Sample document library — 6 PDFs có sẵn trong tests/sample_data/.

Cho sinh viên khiếm thị truy cập nhanh tài liệu STEM phổ biến chỉ bằng giọng nói:
"thư viện" → liệt kê → "vật lý" hoặc "số 1" → load.
"""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel

# Project root: src/data/ → ../..
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = _PROJECT_ROOT / "tests" / "sample_data"


class LibraryItem(BaseModel):
    slug: str
    title: str
    description: str
    filename: str
    voice_aliases: list[str]   # các cách user có thể nói tên này
    ordinal: int               # số thứ tự trong list — user nói "số 1"


# 6 samples đã có sẵn — sắp xếp theo độ phổ biến STEM phổ thông VN
LIBRARY: list[LibraryItem] = [
    LibraryItem(
        slug="physics",
        title="Vật lý — Định luật Newton",
        description="Định luật II Newton về chuyển động, gồm công thức F = ma và biểu đồ lực-gia tốc.",
        filename="sample_physics.pdf",
        voice_aliases=["vật lý", "định luật newton", "niu-tơn", "newton", "lực"],
        ordinal=1,
    ),
    LibraryItem(
        slug="calculus",
        title="Toán — Vi tích phân",
        description="Giới thiệu về tích phân xác định, đạo hàm, và công thức Newton-Leibniz.",
        filename="sample_calculus.pdf",
        voice_aliases=["vi tích phân", "tích phân", "đạo hàm", "calculus"],
        ordinal=2,
    ),
    LibraryItem(
        slug="linear_algebra",
        title="Toán — Đại số tuyến tính",
        description="Phép nhân ma trận, định thức, và hệ phương trình tuyến tính.",
        filename="sample_linear_algebra.pdf",
        voice_aliases=["đại số", "ma trận", "tuyến tính", "linear algebra"],
        ordinal=3,
    ),
    LibraryItem(
        slug="chemistry",
        title="Hoá học — Phản ứng cơ bản",
        description="Phản ứng đốt cháy metan, cân bằng phương trình, năng lượng phản ứng.",
        filename="sample_chemistry.pdf",
        voice_aliases=["hoá", "hóa", "hoá học", "hóa học", "chemistry"],
        ordinal=4,
    ),
    LibraryItem(
        slug="statistics",
        title="Toán — Thống kê và phân phối chuẩn",
        description="Hàm mật độ xác suất, phân phối Gauss, biểu đồ chuẩn.",
        filename="sample_statistics.pdf",
        voice_aliases=["thống kê", "xác suất", "statistics", "phân phối"],
        ordinal=5,
    ),
    LibraryItem(
        slug="wave_physics",
        title="Vật lý — Sóng và dao động",
        description="Phương trình sóng một chiều, bước sóng, tần số, vận tốc truyền sóng.",
        filename="sample_wave_physics.pdf",
        voice_aliases=["sóng", "dao động", "wave", "sóng vật lý"],
        ordinal=6,
    ),
]

# Lookup helpers
_BY_SLUG: dict[str, LibraryItem] = {item.slug: item for item in LIBRARY}


def get_item(slug: str) -> LibraryItem | None:
    """Lookup item by slug; returns None if not found."""
    return _BY_SLUG.get(slug)


def get_path(slug: str) -> Path | None:
    """Get filesystem path to PDF for a slug."""
    item = get_item(slug)
    if not item:
        return None
    p = SAMPLES_DIR / item.filename
    return p if p.exists() else None


def list_all() -> list[LibraryItem]:
    """Return all library items."""
    return list(LIBRARY)


def voice_intro_text() -> str:
    """Generate the spoken text for 'thư viện' command — natural Vietnamese."""
    parts = [f"Thư viện có {len(LIBRARY)} tài liệu."]
    for item in LIBRARY:
        # "Một, Vật lý: Định luật Newton."
        ordinal_word = ["Một", "Hai", "Ba", "Bốn", "Năm", "Sáu"][item.ordinal - 1]
        parts.append(f"{ordinal_word}, {item.title}.")
    parts.append("Hãy nói tên hoặc số thứ tự để tải.")
    return " ".join(parts)
