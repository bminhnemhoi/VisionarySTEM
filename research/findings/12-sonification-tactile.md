# Sonification + Tactile Graphics cho Biểu đồ STEM

## TL;DR
- **Sonification** = chuyển dữ liệu số/biểu đồ → âm thanh (pitch, tempo, timbre).
- **Tactile graphics** = chuyển biểu đồ → hình nổi cảm nhận bằng tay (Braille printer, Dot Pad).
- VisionarySTEM Sprint 8.3 sẽ làm sonification (rẻ, không hardware); tactile via Dot Pad sync (Sprint 6/future).
- **MIT Umwelt** (CHI 2024) là benchmark — interactive accessible chart builder.

## Thiết kế Sonification cơ bản

### Mapping function (line/bar chart 1-D)
```
y-value (data)  →  pitch (MIDI note 60-84, tức C4-C6)
x-position      →  time axis (duration_total / n_points)
data magnitude  →  amplitude (loudness)
```

### Algorithm pseudocode
```python
import numpy as np

def sonify_line_chart(points, duration_s=3.0, sample_rate=22050):
    """points: list of (x, y); returns WAV bytes (mono, 16-bit PCM)."""
    n = len(points)
    samples_per_point = int(duration_s * sample_rate / n)
    
    # Normalize y to [60, 84] MIDI range
    ys = np.array([p[1] for p in points])
    y_min, y_max = ys.min(), ys.max()
    midi_notes = 60 + (ys - y_min) / (y_max - y_min) * 24
    
    audio = []
    for note in midi_notes:
        freq = 440 * (2 ** ((note - 69) / 12))  # MIDI to Hz
        t = np.linspace(0, samples_per_point / sample_rate, samples_per_point)
        tone = 0.4 * np.sin(2 * np.pi * freq * t)
        # Apply attack/release envelope to avoid clicks
        envelope = np.ones_like(tone)
        fade = int(0.05 * len(tone))
        envelope[:fade] = np.linspace(0, 1, fade)
        envelope[-fade:] = np.linspace(1, 0, fade)
        audio.append(tone * envelope)
    
    return np.concatenate(audio)
```

### Cải tiến nâng cao (Sprint 6+)
- **Stereo panning**: x-axis pan trái → phải để cảm nhận "đi từ trái sang phải"
- **Reference tones**: phát "tick" thấp tại x=0, x=max để định vị
- **Multi-series**: 2 đường biểu đồ → 2 timbres khác (sine + square wave)
- **Interactive**: cho user "trỏ" tới x-position cụ thể bằng phím ←→

## So sánh với SOTA

| Tool | Approach | Strength | Limitation |
|------|----------|----------|------------|
| **MIT Umwelt** (CHI 2024) | Multimodal (text + audio + tactile) | Interactive, customizable | Web-only, English |
| **TaleVision** (ICMI 2024) | Tactile-first | Hardware integration | Cần printer chuyên dụng |
| **Sonipy** (Python lib) | Programmatic sonification | Flexible | Manual mapping config |
| **HighCharts Sonification** | Web charts → audio | Production-ready | Commercial |
| **VisionarySTEM Sprint 8.3** | Auto-detect + auto-sonify | Tích hợp pipeline | MVP basic mapping |

## Implementation plan cho Sprint 8.3

### Step 1: Detect sonifiable charts
Chỉ sonify khi `block.type == "chart"` AND chart là 1-D series (line, bar). Skip pie/scatter/heatmap (Sprint 6+).

### Step 2: Extract data points (Gemini)
Prompt: "Trích dữ liệu biểu đồ này thành JSON: `{type: 'line'|'bar', x_label, y_label, points: [[x, y]]}`. Nếu axis có tick rõ, đọc giá trị; nếu không, ước lượng tương đối."

### Step 3: Generate audio
Dùng numpy + scipy.io.wavfile.write. Format MP3 qua `pydub` (FFmpeg dependency) hoặc giữ WAV.

### Step 4: Cache + serve
Cache theo hash(data_points + duration), serve qua endpoint `GET /api/v1/sonify/{block_id}`.

## Tools clone
- `tools/sonipy` (nếu có repo public) — sonification library
- Reference từ MIT Umwelt: https://github.com/mitvis/umwelt (đã có repo)

## Sources
- [MIT Umwelt CHI 2024](https://news.mit.edu/2024/umwelt-enables-interactive-accessible-charts-creation-blind-low-vision-users-0327)
- [Building Multimodal Chart Accessibility (ACM XRDS 2025)](https://dlnext.acm.org/doi/abs/10.1145/3778055)
- [Sonification Handbook](https://sonification.de/handbook/) — academic reference
- [HighCharts Sonification API](https://www.highcharts.com/docs/sonification/getting-started)

## Vấn đề thực tế
- **Quality vs file size**: WAV tốt hơn MP3 cho tone purity nhưng to gấp 10x
- **Browser autoplay**: cần user gesture mới phát được audio, ko auto-play khi load
- **Localization**: title/legend phải đọc tiếng Việt trước khi sonify
