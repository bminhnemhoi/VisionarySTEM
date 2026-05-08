"""Tests for src.core.sonification — Sprint 8.3."""
import io
import wave

import pytest


def test_sonify_points_returns_valid_wav():
    from src.core.sonification import sonify_points
    pts = [(i, float(i % 5)) for i in range(8)]
    wav = sonify_points(pts, duration_s=1.0)
    assert wav[:4] == b"RIFF"
    assert b"WAVE" in wav[:12]


def test_sonify_points_duration_correct():
    from src.core.sonification import sonify_points
    pts = [(i, float(i)) for i in range(5)]
    duration = 2.0
    wav = sonify_points(pts, duration_s=duration, sample_rate=22050)
    with wave.open(io.BytesIO(wav), "rb") as wf:
        n_frames = wf.getnframes()
        actual_dur = n_frames / wf.getframerate()
        # tolerance because of attack/release + initial tick
        assert duration <= actual_dur <= duration + 0.5


def test_sonify_empty_points_returns_silence():
    from src.core.sonification import sonify_points
    wav = sonify_points([], duration_s=1.0)
    assert wav[:4] == b"RIFF"
    assert len(wav) > 0


def test_sonify_single_point_handles_gracefully():
    from src.core.sonification import sonify_points
    wav = sonify_points([(0, 1.0)], duration_s=1.0)
    assert wav[:4] == b"RIFF"


def test_sonify_constant_y_no_division_error():
    from src.core.sonification import sonify_points
    pts = [(i, 5.0) for i in range(10)]  # all same y
    wav = sonify_points(pts, duration_s=1.0)
    assert wav[:4] == b"RIFF"


def test_sonify_block_rejects_non_chart(sample_blocks):
    from src.core.sonification import sonify_block
    text_block = next(b for b in sample_blocks if b.type == "text")
    with pytest.raises(ValueError, match="not a chart"):
        sonify_block(text_block)


def test_sonify_block_with_pre_extracted_data(sample_blocks):
    """If sonification_data already populated, skip Gemini call."""
    from src.core.sonification import sonify_block
    chart_block = next(b for b in sample_blocks if b.type == "chart")
    chart_block.sonification_data = {
        "chart_type": "line",
        "x_label": "Gia tốc",
        "y_label": "Lực",
        "points": [[i, float(i * 2)] for i in range(8)],
    }
    wav, data = sonify_block(chart_block, duration_s=1.0)
    assert wav[:4] == b"RIFF"
    assert data.chart_type == "line"
    assert len(data.points) == 8
