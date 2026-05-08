"""
VisionarySTEM - Document Processor
=====================================
Orchestrates the full document analysis pipeline:
PDF/Image → Gemini Analysis → Structured JSON → Spatial Index

Phase: Sprint 2 — async parallel page processing.
"""

import asyncio
import time
import logging
from pathlib import Path
from collections import defaultdict
from typing import AsyncIterator, Optional

import fitz  # PyMuPDF

from src.config import GEMINI_MODEL
from src.core.gemini_engine import get_engine, GeminiAnalysisResult
from src.api.schemas import (
    ContentBlock,
    Coordinates,
    DocumentAnalysisResponse,
    DocumentMetadata,
    SpatialIndex,
)

logger = logging.getLogger(__name__)

# Tunable: max concurrent Gemini calls per document
MAX_CONCURRENT_PAGES = 4


def _get_page_count(file_path: Path) -> int:
    """Number of pages in PDF; 1 for images."""
    if file_path.suffix.lower() == ".pdf":
        doc = fitz.open(str(file_path))
        count = doc.page_count
        doc.close()
        return count
    return 1


def _build_spatial_index(blocks: list[ContentBlock]) -> SpatialIndex:
    regions: dict[str, list[str]] = defaultdict(list)
    for block in blocks:
        regions[block.coordinates.region].append(block.id)
    return SpatialIndex(regions=dict(regions))


def _convert_gemini_to_schema(gemini_blocks, page_override: int = None) -> list[ContentBlock]:
    result = []
    for gb in gemini_blocks:
        coords = Coordinates(
            page=page_override or gb.coordinates.page,
            x=gb.coordinates.x,
            y=gb.coordinates.y,
            w=gb.coordinates.w,
            h=gb.coordinates.h,
            region=gb.coordinates.region,
        )
        result.append(ContentBlock(
            id=gb.id,
            type=gb.type,
            raw_content=gb.raw_content,
            latex=gb.latex,
            spoken_text=gb.spoken_text,
            language="vi",
            confidence=gb.confidence,
            coordinates=coords,
        ))
    return result


def _render_page_jpeg(file_path: Path, page_num: int) -> bytes:
    """Render PDF page (or image) to compressed JPEG bytes. Sync I/O."""
    doc = fitz.open(str(file_path))
    page = doc[page_num]
    zoom = min(2.5, 1500.0 / max(page.rect.width, page.rect.height))
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg", jpg_quality=85)
    doc.close()
    return img_bytes


async def _analyze_page_async(
    file_path: Path,
    page_num: int,
    semaphore: asyncio.Semaphore,
) -> tuple[int, GeminiAnalysisResult]:
    """Render + analyze one page; gated by semaphore. Returns (page_idx, result)."""
    async with semaphore:
        # Render page in thread pool (PyMuPDF is sync C-extension, fast)
        img_bytes = await asyncio.to_thread(_render_page_jpeg, file_path, page_num)
        logger.info(f"[page {page_num + 1}] rendered {len(img_bytes) // 1024} KB; calling Gemini...")
        engine = get_engine()
        # Gemini SDK is sync; offload to thread to keep loop free
        result = await asyncio.to_thread(
            engine.analyze_image_bytes,
            img_bytes,
            "image/jpeg",
            page_num + 1,
        )
        logger.info(f"[page {page_num + 1}] Gemini returned {len(result.content_blocks)} blocks")
        return page_num, result


def _renumber_blocks_globally(pages_results: list[tuple[int, GeminiAnalysisResult]]) -> list[ContentBlock]:
    """Sort by page, flatten, renumber block_001, block_002, ... globally."""
    pages_results.sort(key=lambda x: x[0])
    all_blocks: list[ContentBlock] = []
    for page_idx, gemini_result in pages_results:
        page_blocks = _convert_gemini_to_schema(gemini_result.content_blocks, page_override=page_idx + 1)
        for i, block in enumerate(page_blocks):
            block.id = f"block_{len(all_blocks) + i + 1:03d}"
        all_blocks.extend(page_blocks)
    return all_blocks


async def analyze_file_async(
    file_path: str,
    filename: Optional[str] = None,
    max_concurrent: int = MAX_CONCURRENT_PAGES,
) -> DocumentAnalysisResponse:
    """Async pipeline with parallel page processing. Target: 19s → <5s p95."""
    start_time = time.time()
    file_path = Path(file_path)
    if filename is None:
        filename = file_path.name

    total_pages = _get_page_count(file_path)
    logger.info(f"Async pipeline start: {filename} ({total_pages} pages, max_concurrent={max_concurrent})")

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [_analyze_page_async(file_path, p, semaphore) for p in range(total_pages)]
    pages_results = await asyncio.gather(*tasks)

    all_blocks = _renumber_blocks_globally(list(pages_results))
    spatial_index = _build_spatial_index(all_blocks)
    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(f"Async pipeline done: {len(all_blocks)} blocks, {elapsed_ms}ms, {len(spatial_index.regions)} regions")
    return DocumentAnalysisResponse(
        document_metadata=DocumentMetadata(
            filename=filename,
            total_pages=total_pages,
            processing_time_ms=elapsed_ms,
            model_used=GEMINI_MODEL,
        ),
        content_blocks=all_blocks,
        spatial_index=spatial_index,
    )


async def stream_blocks_async(
    file_path: str,
    filename: Optional[str] = None,
    max_concurrent: int = MAX_CONCURRENT_PAGES,
) -> AsyncIterator[dict]:
    """
    Yield events as pages complete: status, block (per-block), done.
    Used by SSE endpoint for time-to-first-block <1s.
    """
    start_time = time.time()
    file_path = Path(file_path)
    if filename is None:
        filename = file_path.name

    total_pages = _get_page_count(file_path)
    yield {"event": "status", "data": {"phase": "started", "total_pages": total_pages, "filename": filename}}

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [
        asyncio.create_task(_analyze_page_async(file_path, p, semaphore))
        for p in range(total_pages)
    ]

    completed_pages: list[tuple[int, GeminiAnalysisResult]] = []
    block_counter = 0

    for task in asyncio.as_completed(tasks):
        page_idx, gemini_result = await task
        # Convert + renumber relative to *current* state — note: order may not match final
        page_blocks = _convert_gemini_to_schema(gemini_result.content_blocks, page_override=page_idx + 1)
        for block in page_blocks:
            block_counter += 1
            block.id = f"block_{block_counter:03d}"
            yield {"event": "block", "data": block.model_dump()}
        completed_pages.append((page_idx, gemini_result))
        yield {"event": "page_done", "data": {"page": page_idx + 1, "blocks_in_page": len(page_blocks)}}

    # Final summary
    all_blocks = _renumber_blocks_globally(completed_pages)
    spatial_index = _build_spatial_index(all_blocks)
    elapsed_ms = int((time.time() - start_time) * 1000)
    yield {
        "event": "done",
        "data": {
            "total_blocks": len(all_blocks),
            "total_pages": total_pages,
            "processing_time_ms": elapsed_ms,
            "spatial_index": spatial_index.model_dump(),
            "model_used": GEMINI_MODEL,
        },
    }


def analyze_file(file_path: str, filename: Optional[str] = None) -> DocumentAnalysisResponse:
    """Sync wrapper around async pipeline (backward compat for scripts/tests)."""
    return asyncio.run(analyze_file_async(file_path, filename))
