"""
VisionarySTEM Gemini TTS — giọng đọc tự nhiên, có cảm xúc.

Thay thế Edge TTS (giọng máy) bằng Gemini 2.5 TTS.
- Hỗ trợ inline emotion tags: [warmly], [excitedly], [calmly], [empathetically]
- Hỗ trợ tiếng Việt với 30+ voice (Aoede, Despina, Charon, ...)
- Fallback sang Edge TTS nếu Gemini lỗi/quota
- Cache theo hash(text+voice+style) để tiết kiệm

Reference: https://ai.google.dev/gemini-api/docs/speech-generation
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import wave
from pathlib import Path
from typing import Literal, Optional

from google.genai import types

from src.config import OUTPUT_DIR, GEMINI_MODEL
from src.core.gemini_engine import get_engine
from src.tts.edge_tts_engine import generate_speech_async as edge_speak

logger = logging.getLogger(__name__)


# Model TTS — preview mới hỗ trợ emotion control
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_TTS_PRO_MODEL = "gemini-2.5-pro-preview-tts"

# Default voice cho tiếng Việt — chọn voice ấm áp tự nhiên
# Test thực tế: Aoede (breezy/warm), Despina (smooth), Leda (gentle)
DEFAULT_VOICE = "Aoede"

# Voice mood → Gemini inline tag (hoặc style instruction)
MOOD_PRESETS: dict[str, str] = {
    "neutral": "",
    "warm": "[warmly]",          # ấm áp, gần gũi
    "calm": "[calmly]",          # bình tĩnh, từ tốn
    "empathetic": "[empathetically]",  # đồng cảm
    "encouraging": "[encouragingly]",  # khuyến khích
    "excited": "[excitedly]",    # hào hứng (cho thông báo good news)
    "thoughtful": "[thoughtfully]",  # suy tư, dùng khi giải thích
    "friendly": "[in a friendly tone]",
}

# All available Gemini TTS voices (cho user chọn)
ALL_VOICES = [
    "Aoede", "Despina", "Charon", "Puck", "Kore", "Fenrir",
    "Leda", "Orus", "Zephyr", "Erinome",
]


def _cache_key(text: str, voice: str, mood: str) -> str:
    return hashlib.sha1(f"gemini|{voice}|{mood}|{text}".encode("utf-8")).hexdigest()[:16]


def _cache_path(text: str, voice: str, mood: str) -> Path:
    cache_dir = OUTPUT_DIR / "gemini_tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{_cache_key(text, voice, mood)}.wav"


def _pcm_to_wav_bytes(pcm: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw PCM 16-bit mono into a proper WAV file."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _build_prompt(text: str, mood: str = "warm") -> str:
    """Prepend emotion tag + soft instruction to make TTS sound human."""
    tag = MOOD_PRESETS.get(mood, "")
    if tag:
        return f"{tag} {text}"
    return text


def _gemini_tts_sync(
    text: str,
    voice: str = DEFAULT_VOICE,
    mood: str = "warm",
) -> bytes:
    """Sync Gemini TTS call. Returns WAV bytes (24kHz mono 16-bit)."""
    engine = get_engine()
    prompt = _build_prompt(text, mood)

    response = engine.client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        ),
    )
    parts = response.candidates[0].content.parts
    if not parts or not parts[0].inline_data:
        raise RuntimeError("Gemini TTS returned no audio data")

    pcm = parts[0].inline_data.data
    return _pcm_to_wav_bytes(pcm)


async def gemini_speak_async(
    text: str,
    voice: str = DEFAULT_VOICE,
    mood: str = "warm",
    use_cache: bool = True,
) -> bytes:
    """
    Generate Vietnamese speech with emotion via Gemini TTS.
    Returns WAV bytes (browser-compatible).

    Falls back to Edge TTS if Gemini fails (quota, error, etc.)
    """
    if use_cache:
        cache_file = _cache_path(text, voice, mood)
        if cache_file.exists() and cache_file.stat().st_size > 0:
            return cache_file.read_bytes()

    try:
        # Run sync Gemini call in thread (SDK is sync)
        wav = await asyncio.to_thread(_gemini_tts_sync, text, voice, mood)
        if use_cache:
            _cache_path(text, voice, mood).write_bytes(wav)
        logger.info(f"[gemini_tts] Generated {len(wav)} bytes (voice={voice}, mood={mood})")
        return wav
    except Exception as e:
        logger.warning(f"[gemini_tts] Failed, falling back to Edge: {e}")
        # Fallback to Edge TTS
        edge_path = await edge_speak(text)
        return Path(edge_path).read_bytes()


def gemini_speak(text: str, voice: str = DEFAULT_VOICE, mood: str = "warm") -> bytes:
    """Sync wrapper."""
    return asyncio.run(gemini_speak_async(text, voice, mood))


# ============================================================
# Heuristic mood detection from text
# ============================================================
def auto_detect_mood(text: str) -> str:
    """
    Pick a mood automatically based on text content.
    Useful when frontend doesn't specify mood explicitly.
    """
    t = text.lower()
    # Greeting / welcome
    if any(w in t for w in ["chào", "xin chào", "hân hạnh", "chào mừng"]):
        return "warm"
    # Question / explanation
    if "?" in t or any(w in t for w in ["định nghĩa", "có nghĩa là", "giải thích", "công thức"]):
        return "thoughtful"
    # Encouraging
    if any(w in t for w in ["bạn làm tốt", "tuyệt vời", "đúng rồi", "chúc mừng"]):
        return "encouraging"
    # Apology / empathy
    if any(w in t for w in ["xin lỗi", "rất tiếc", "không sao"]):
        return "empathetic"
    # Default: warm conversational
    return "warm"
