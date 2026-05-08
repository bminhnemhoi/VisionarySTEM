"""
VisionarySTEM - Edge TTS Engine
==================================
Text-to-Speech engine using Microsoft Edge TTS.
Generates natural Vietnamese speech from spoken_text.

Sprint 2 additions:
- Hash-based MP3 cache (skip regenerate)
- Rate / pitch parameters for accessibility (blind users often want 1.5-2x speed)
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional

import edge_tts

from src.config import TTS_VOICE, OUTPUT_DIR

logger = logging.getLogger(__name__)


def _cache_key(text: str, voice: str, rate: str, pitch: str) -> str:
    h = hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()[:16]
    return h


def _cache_path(text: str, voice: str, rate: str, pitch: str) -> Path:
    key = _cache_key(text, voice, rate, pitch)
    return OUTPUT_DIR / "tts_cache" / f"{key}.mp3"


async def generate_speech_async(
    text: str,
    output_path: Optional[str] = None,
    voice: str = TTS_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> str:
    """
    Generate speech audio. If output_path is None, uses content-addressed cache.

    rate: e.g. "+0%", "+50%", "-20%" — accessibility (blind users prefer faster)
    pitch: e.g. "+0Hz", "+5Hz", "-10Hz"
    """
    if output_path is None:
        path = _cache_path(text, voice, rate, pitch)
    else:
        path = Path(output_path)

    path.parent.mkdir(parents=True, exist_ok=True)

    # Cache hit — skip regeneration
    if output_path is None and path.exists() and path.stat().st_size > 0:
        logger.info(f"TTS cache hit: {path.name}")
        return str(path)

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(path))
    logger.info(f"TTS generated: {path}")
    return str(path)


async def get_or_create_speech(
    text: str,
    voice: str = TTS_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    """Cache-first lookup; returns Path. Used by API for streaming response."""
    path = _cache_path(text, voice, rate, pitch)
    if path.exists() and path.stat().st_size > 0:
        return path
    await generate_speech_async(text, str(path), voice, rate, pitch)
    return path


def generate_speech(
    text: str,
    output_path: Optional[str] = None,
    voice: str = TTS_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> str:
    """Sync wrapper."""
    return asyncio.run(generate_speech_async(text, output_path, voice, rate, pitch))


async def generate_block_audio(
    blocks: list[dict],
    output_dir: Optional[str] = None,
    voice: str = TTS_VOICE,
) -> list[dict]:
    """Batch generate audio for content blocks. Returns [{block_id, audio_path}, ...]."""
    if output_dir is None:
        output_dir = str(OUTPUT_DIR)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    for block in blocks:
        block_id = block.get("id", "unknown")
        spoken_text = block.get("spoken_text", "")
        if not spoken_text:
            continue
        audio_path = str(Path(output_dir) / f"{block_id}.mp3")
        try:
            await generate_speech_async(spoken_text, audio_path, voice)
            results.append({"block_id": block_id, "audio_path": audio_path})
        except Exception as e:
            logger.error(f"TTS failed for {block_id}: {e}")
    return results


# ============================================
# CLI Demo
# ============================================
if __name__ == "__main__":
    print("VisionarySTEM TTS Engine Demo")
    print("=" * 50)
    test_texts = [
        "Định luật hai Niu-tơn về chuyển động.",
        "Lực bằng khối lượng nhân gia tốc.",
        "Năng lượng bằng khối lượng nhân bình phương tốc độ ánh sáng.",
    ]
    for i, text in enumerate(test_texts):
        output = generate_speech(text, str(OUTPUT_DIR / f"demo_{i+1}.mp3"))
        print(f"  Generated: {output}")
    print("\nDemo complete!")
