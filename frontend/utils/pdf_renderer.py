"""
Render PDF pages to PNG bytes for Streamlit display.
Used to overlay bounding boxes on top of the rendered page.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont


def render_page_png(file_bytes: bytes, page_number: int = 1, max_dim: int = 1200) -> bytes:
    """Render given PDF/image bytes → PNG bytes. page_number is 1-indexed."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        # Fallback: image input
        return file_bytes

    page = doc[page_number - 1]
    zoom = min(2.0, max_dim / max(page.rect.width, page.rect.height))
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    png = pix.tobytes("png")
    doc.close()
    return png


def overlay_bounding_boxes(
    png_bytes: bytes,
    blocks: list[dict],
    page_number: int = 1,
    highlight_block_id: Optional[str] = None,
) -> bytes:
    """
    Draw bounding boxes from blocks (coordinates in % 0-100) onto the PNG.
    `highlight_block_id` is drawn in a distinctive color.
    """
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    W, H = img.size

    type_color = {
        "text":   (66, 133, 244, 100),    # blue
        "math":   (219, 68, 55, 130),     # red
        "chart":  (15, 157, 88, 110),     # green
        "table":  (244, 180, 0, 110),     # yellow
        "figure": (171, 71, 188, 110),    # purple
    }
    border_color = {
        "text":   (66, 133, 244, 255),
        "math":   (219, 68, 55, 255),
        "chart":  (15, 157, 88, 255),
        "table":  (244, 180, 0, 255),
        "figure": (171, 71, 188, 255),
    }

    try:
        font = ImageFont.truetype("arial.ttf", size=14)
    except OSError:
        font = ImageFont.load_default()

    for block in blocks:
        if block.get("coordinates", {}).get("page", 1) != page_number:
            continue
        coord = block["coordinates"]
        x0 = int(coord["x"] / 100 * W)
        y0 = int(coord["y"] / 100 * H)
        x1 = int((coord["x"] + coord["w"]) / 100 * W)
        y1 = int((coord["y"] + coord["h"]) / 100 * H)
        is_highlight = block["id"] == highlight_block_id
        fill = (255, 235, 59, 180) if is_highlight else type_color.get(block["type"], (200, 200, 200, 80))
        border = (255, 152, 0, 255) if is_highlight else border_color.get(block["type"], (100, 100, 100, 255))
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=border, width=3)
        draw.text((x0 + 4, y0 + 2), block["id"], fill=(0, 0, 0, 255), font=font)

    composed = Image.alpha_composite(img, overlay).convert("RGB")
    out = io.BytesIO()
    composed.save(out, format="PNG", optimize=True)
    return out.getvalue()
