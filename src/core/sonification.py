"""
VisionarySTEM Sonification — Sprint 8.3
=========================================
Convert chart data to audio (line/bar charts → pitch sequence).
Pattern from research/findings/12-sonification-tactile.md (MIT Umwelt-style).
"""

from __future__ import annotations

import io
import json
import logging
import struct
import wave
from typing import Optional

import numpy as np
from google.genai import types
from pydantic import BaseModel, Field

from src.api.schemas import ContentBlock
from src.core.gemini_engine import get_engine

logger = logging.getLogger(__name__)


# ============================================================
# Chart data extraction (Gemini)
# ============================================================

CHART_EXTRACT_PROMPT = """Phân tích biểu đồ này và trích xuất dữ liệu thành JSON.

Yêu cầu:
- Xác định loại biểu đồ ("line", "bar", "scatter", "pie", "other")
- Đọc nhãn trục X và Y nếu có
- Trích xuất 5-20 điểm dữ liệu (x, y) — nếu axis có tick rõ thì đọc giá trị; nếu không thì ước lượng tương đối (0.0 - 1.0)
- Trả về object có: chart_type, x_label, y_label, points[]

Nếu không phải biểu đồ 1-D (line/bar) thì trả chart_type="other" và points rỗng."""


class ChartData(BaseModel):
    chart_type: str
    x_label: str = ""
    y_label: str = ""
    points: list[list[float]] = Field(
        default_factory=list,
        description="List of [x, y] pairs",
    )


def extract_chart_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> ChartData:
    """Use Gemini to extract data points from a chart image."""
    engine = get_engine()
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    response = engine.client.models.generate_content(
        model=engine.model,
        contents=[image_part, CHART_EXTRACT_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChartData,
            temperature=0.1,
        ),
    )
    result = response.parsed
    if result is None:
        try:
            result = ChartData(**json.loads(response.text))
        except Exception as e:
            logger.warning(f"Chart extraction parse failed: {e}")
            result = ChartData(chart_type="other")
    return result


# ============================================================
# Audio generation
# ============================================================

def sonify_points(
    points: list[tuple[float, float]],
    duration_s: float = 3.0,
    sample_rate: int = 22050,
    pitch_min_midi: int = 60,  # C4
    pitch_max_midi: int = 84,  # C6
) -> bytes:
    """
    Generate WAV bytes from a list of (x, y) points.
    Maps y values to MIDI pitch, x position to time.
    """
    if not points or len(points) < 2:
        # Empty: 0.5s silence
        n = int(0.5 * sample_rate)
        silent = np.zeros(n, dtype=np.float32)
        return _to_wav_bytes(silent, sample_rate)

    # Sort by x ascending
    sorted_pts = sorted(points, key=lambda p: p[0])
    ys = np.array([p[1] for p in sorted_pts], dtype=np.float64)

    y_min, y_max = ys.min(), ys.max()
    if y_max - y_min < 1e-9:
        # All same y → middle pitch
        midi_notes = np.full_like(ys, (pitch_min_midi + pitch_max_midi) / 2)
    else:
        midi_notes = pitch_min_midi + (ys - y_min) / (y_max - y_min) * (pitch_max_midi - pitch_min_midi)

    n_total = int(duration_s * sample_rate)
    samples_per_point = max(1, n_total // len(sorted_pts))
    fade = max(20, int(0.04 * samples_per_point))  # 40ms attack/release

    audio_chunks = []
    for note in midi_notes:
        freq = 440.0 * (2 ** ((note - 69) / 12))  # MIDI → Hz
        t = np.linspace(0, samples_per_point / sample_rate, samples_per_point, endpoint=False)
        wave_data = 0.45 * np.sin(2 * np.pi * freq * t)
        # Envelope to avoid clicks
        env = np.ones(samples_per_point, dtype=np.float64)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        audio_chunks.append(wave_data * env)

    audio = np.concatenate(audio_chunks).astype(np.float32)
    # Add a brief reference "tick" at start (low note) so listener knows beginning
    tick = _generate_tick(sample_rate, freq=200, duration_s=0.08, amplitude=0.3)
    silence_gap = np.zeros(int(0.05 * sample_rate), dtype=np.float32)
    full = np.concatenate([tick, silence_gap, audio])
    return _to_wav_bytes(full, sample_rate)


def _generate_tick(
    sample_rate: int,
    freq: float = 200,
    duration_s: float = 0.08,
    amplitude: float = 0.3,
) -> np.ndarray:
    """Short reference tone."""
    t = np.linspace(0, duration_s, int(duration_s * sample_rate), endpoint=False)
    tone = amplitude * np.sin(2 * np.pi * freq * t)
    fade = int(0.01 * sample_rate)
    if len(tone) > 2 * fade:
        tone[:fade] *= np.linspace(0, 1, fade)
        tone[-fade:] *= np.linspace(1, 0, fade)
    return tone.astype(np.float32)


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 numpy array to 16-bit PCM WAV bytes."""
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


# ============================================================
# High-level: from a ContentBlock to WAV bytes
# ============================================================

def sonify_block(
    block: ContentBlock,
    page_image_bytes: Optional[bytes] = None,
    duration_s: float = 3.0,
) -> tuple[bytes, ChartData]:
    """
    Generate sonification audio for a chart block.

    If `block.sonification_data` already populated, use it.
    Otherwise (and if page_image_bytes provided) extract via Gemini.

    Returns (wav_bytes, chart_data_used).
    """
    if block.type != "chart":
        raise ValueError(f"Block {block.id} is not a chart (type={block.type})")

    chart_data: Optional[ChartData] = None
    if block.sonification_data:
        try:
            chart_data = ChartData(**block.sonification_data)
        except Exception:
            chart_data = None

    if chart_data is None or not chart_data.points:
        if page_image_bytes is None:
            # Fallback: generate from spoken_text length only (a tone modulated by sentence length)
            chart_data = ChartData(chart_type="line", points=_fallback_synthetic_data())
        else:
            chart_data = extract_chart_data(page_image_bytes)
            block.sonification_data = chart_data.model_dump()

    # Convert points to tuple list
    pts = [(float(p[0]), float(p[1])) for p in chart_data.points if len(p) >= 2]
    wav = sonify_points(pts, duration_s=duration_s)
    return wav, chart_data


def _fallback_synthetic_data() -> list[list[float]]:
    """Trivial sine-like 1-period data for when extraction fails."""
    return [[i, float(np.sin(i * 0.6) + 1)] for i in range(10)]
