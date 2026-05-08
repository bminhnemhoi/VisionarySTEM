"""
VisionarySTEM frontend → backend API client.

Wraps REST + SSE so app.py stays clean.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Generator, Optional
from urllib.parse import urlencode

import requests

API_BASE = os.getenv("VS_API_BASE", "http://localhost:8000/api/v1")
TIMEOUT_SECONDS = 120


@dataclass
class AnalyzeResult:
    document_id: str
    blocks: list[dict]
    spatial_index: dict
    metadata: dict


def health() -> dict:
    r = requests.get(f"{API_BASE}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def mock_analyze() -> AnalyzeResult:
    r = requests.get(f"{API_BASE}/mock/analyze", timeout=30)
    r.raise_for_status()
    data = r.json()
    return AnalyzeResult(
        document_id="mock_doc",
        blocks=data["content_blocks"],
        spatial_index=data["spatial_index"],
        metadata=data["document_metadata"],
    )


def analyze_file_blocking(file_bytes: bytes, filename: str) -> AnalyzeResult:
    """One-shot blocking analyze. Use stream version when possible."""
    files = {"file": (filename, file_bytes)}
    r = requests.post(f"{API_BASE}/analyze", files=files, timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    doc_id = data.get("document_id") or r.headers.get("X-Document-Id", "")
    return AnalyzeResult(
        document_id=doc_id,
        blocks=data["content_blocks"],
        spatial_index=data["spatial_index"],
        metadata=data["document_metadata"],
    )


def analyze_file_stream(
    file_bytes: bytes,
    filename: str,
) -> Generator[tuple[str, dict], None, None]:
    """
    Stream analyze events from /analyze/stream (SSE).
    Yields (event_name, data_dict) tuples.
    Events: status, block, page_done, done, document_id, error.
    """
    files = {"file": (filename, file_bytes)}
    with requests.post(
        f"{API_BASE}/analyze/stream",
        files=files,
        stream=True,
        timeout=TIMEOUT_SECONDS,
    ) as r:
        r.raise_for_status()
        event_name: str | None = None
        data_buffer: list[str] = []

        for raw_line in r.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            if raw_line == "":
                # Dispatch buffered event
                if event_name and data_buffer:
                    try:
                        data = json.loads("\n".join(data_buffer))
                    except json.JSONDecodeError:
                        data = {"raw": "\n".join(data_buffer)}
                    yield event_name, data
                event_name = None
                data_buffer = []
                continue

            if raw_line.startswith("event:"):
                event_name = raw_line.split(":", 1)[1].strip()
            elif raw_line.startswith("data:"):
                data_buffer.append(raw_line.split(":", 1)[1].lstrip())


def query_spatial(query: str, document_id: Optional[str] = None) -> dict:
    payload = {"query": query}
    if document_id:
        payload["document_id"] = document_id
    r = requests.post(f"{API_BASE}/query", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def _build_qs(rate: str, pitch: str, document_id: Optional[str]) -> str:
    """URL-encode params correctly. `+` and `%` must be percent-encoded for query strings."""
    params = {"rate": rate, "pitch": pitch}
    if document_id:
        params["document_id"] = document_id
    return "?" + urlencode(params, safe="")


def tts_block_url(block_id: str, document_id: Optional[str] = None,
                   rate: str = "+0%", pitch: str = "+0Hz") -> str:
    return f"{API_BASE}/tts/block/{block_id}{_build_qs(rate, pitch, document_id)}"


def tts_page_url(page: int, document_id: Optional[str] = None,
                  rate: str = "+0%", pitch: str = "+0Hz") -> str:
    return f"{API_BASE}/tts/page/{page}{_build_qs(rate, pitch, document_id)}"


def tts_speak(text: str, rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
    """Generate TTS audio for arbitrary text. Returns MP3 bytes."""
    r = requests.post(
        f"{API_BASE}/tts/speak",
        params={"text": text, "rate": rate, "pitch": pitch},
        timeout=30,
    )
    r.raise_for_status()
    return r.content
