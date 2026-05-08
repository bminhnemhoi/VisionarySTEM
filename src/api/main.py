"""
VisionarySTEM - FastAPI Application (Phase 2)
==============================================
REST API entry point for the VisionarySTEM backend.
Provides endpoints for document analysis, spatial queries, TTS audio, and health checks.

Điểm vào REST API cho backend VisionarySTEM.
Cung cấp endpoint phân tích tài liệu, truy vấn không gian, âm thanh TTS, và kiểm tra sức khỏe.
"""

import json
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.config import (
    GEMINI_MODEL,
    MAX_FILE_SIZE_BYTES,
    UPLOAD_DIR,
    OUTPUT_DIR,
    ALLOWED_ORIGINS,
    TENANT_MODE,
    print_config_summary,
)
from src.auth import TenantContext, get_tenant_context
from src.api.schemas import (
    DocumentAnalysisResponse,
    HealthResponse,
    ErrorResponse,
    SpatialQueryRequest,
    SpatialQueryResponse,
    ContentBlock,
    Coordinates,
    DocumentMetadata,
    SpatialIndex,
    ChatRequest,
    ChatResponse,
    CameraSnapshotResponse,
)
from src.core.document_processor import analyze_file, analyze_file_async, stream_blocks_async
from src.core.spatial_rag import get_rag_engine
from src.tts.edge_tts_engine import generate_speech_async, get_or_create_speech
from src.tts.gemini_tts import gemini_speak_async, auto_detect_mood, ALL_VOICES, MOOD_PRESETS, DEFAULT_VOICE
from src.core.tutor import get_tutor
from src.core.critique import get_critique
from src.core.sonification import sonify_block, ChartData
from src.core.gemini_engine import get_engine as get_gemini_engine
from src.core.qa import answer_question, QAResponse
from src.core.web_search import google_search, WebSearchResult
from src.agents.planner import make_plan
from src.agents.executor import execute_plan_sse
from src.export import build_epub3, latex_to_braille, text_to_braille_unicode
from src.export.epub3 import latex_to_mathml
from src.data.library import LIBRARY, get_path as library_get_path, list_all as library_list_all

# ============================================
# Configure logging
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VisionarySTEM")

# ============================================
# Lifespan (replaces deprecated @app.on_event)
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print_config_summary()
    logger.info("VisionarySTEM API v2.1.0 is ready!")
    logger.info("API docs: http://localhost:8000/docs")
    yield
    logger.info("VisionarySTEM API shutting down")


# ============================================
# FastAPI Application
# ============================================
app = FastAPI(
    title="VisionarySTEM API",
    description=(
        "Multimodal AI Agent for Visually Impaired STEM Students\n\n"
        "Tro ly AI da phuong thuc cho sinh vien khiem thi khoi STEM.\n\n"
        "**Powered by Gemini 2.5 Flash** - Native Multimodal Analysis\n\n"
        "Sprint 3+4: Streaming SSE + Multi-tenant ready"
    ),
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware – use concrete origins from config + auto-add 127.0.0.1 mirrors of localhost
def _expand_origins(origins: list[str]) -> list[str]:
    """For each `localhost:PORT` add matching `127.0.0.1:PORT` (and vice versa)."""
    expanded = list(origins)
    for o in origins:
        if "://localhost" in o:
            expanded.append(o.replace("://localhost", "://127.0.0.1"))
        elif "://127.0.0.1" in o:
            expanded.append(o.replace("://127.0.0.1", "://localhost"))
    return list(dict.fromkeys(expanded))  # dedupe preserving order


app.add_middleware(
    CORSMiddleware,
    allow_origins=_expand_origins(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Document-Id"],
    expose_headers=["X-Document-Id"],
)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

# Per-document store keyed by document_id (instead of single global)
# Trong production multi-tenant sẽ thay bằng Redis/DB. Hiện tại: in-memory cho single-tenant demo.
_analyses: dict[str, "DocumentAnalysisResponse"] = {}
# Document_id mới nhất (fallback khi client không gửi document_id)
_latest_document_id: str | None = None


def _store_analysis(doc_id: str, response: "DocumentAnalysisResponse") -> None:
    """Save analysis response indexed by document_id."""
    global _latest_document_id
    _analyses[doc_id] = response
    _latest_document_id = doc_id


def _get_analysis(doc_id: str | None) -> "DocumentAnalysisResponse | None":
    """Lookup by id; fall back to most recent if id missing."""
    if doc_id and doc_id in _analyses:
        return _analyses[doc_id]
    if _latest_document_id:
        return _analyses.get(_latest_document_id)
    return None


# ============================================
# SYSTEM ENDPOINTS
# ============================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect bare host to interactive API docs."""
    return RedirectResponse(url="/docs", status_code=307)


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health Check / Kiem tra suc khoe",
    tags=["System"],
)
async def health_check(tenant: TenantContext = Depends(get_tenant_context)):
    """
    Check if the API is running and return service info.
    Includes tenant context (default in single mode).
    """
    return HealthResponse(
        status="ok",
        service="VisionarySTEM API",
        version="2.1.0",
        gemini_model=GEMINI_MODEL,
    )


# ============================================
# ANALYSIS ENDPOINTS
# ============================================

@app.post(
    "/api/v1/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze STEM Document / Phan tich tai lieu STEM",
    tags=["Analysis"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Analysis failed"},
    },
)
async def analyze_document(file: UploadFile = File(...)):
    """
    Upload a PDF or image file for STEM document analysis.
    Returns structured JSON with content blocks, coordinates, and spatial index.
    Automatically indexes results into Spatial RAG for voice queries.

    Tai len file PDF hoac anh de phan tich tai lieu STEM.
    Tra ve JSON co cau truc voi cac khoi noi dung, toa do, va chi muc khong gian.
    Tu dong lap chi muc ket qua vao Spatial RAG cho truy van giong noi.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save uploaded file temporarily
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    temp_path = UPLOAD_DIR / safe_filename

    try:
        # Read and check file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB"
            )

        # Write to disk
        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(f"File saved: {temp_path} ({len(content)} bytes)")

        # Run analysis pipeline (async parallel pages)
        result = await analyze_file_async(
            file_path=str(temp_path),
            filename=file.filename,
        )

        # Auto-index into Spatial RAG for voice queries
        doc_id = unique_id
        rag_engine = get_rag_engine()
        rag_engine.index_document(doc_id, result.content_blocks)

        # Register with tutor so /chat can reference blocks
        get_tutor().register_document(doc_id, result)

        # Store reference for subsequent queries
        _store_analysis(doc_id, result)

        # Attach document_id to response metadata for client to track
        result.document_metadata.filename = file.filename or result.document_metadata.filename
        logger.info(f"Indexed into Spatial RAG + Tutor: doc_id={doc_id}")

        # Wrap response with document_id header for frontend
        from fastapi.responses import JSONResponse
        body = result.model_dump()
        body["document_id"] = doc_id
        return JSONResponse(content=body, headers={"X-Document-Id": doc_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
            logger.info(f"Temp file cleaned up: {temp_path}")


@app.post(
    "/api/v1/analyze/stream",
    summary="Stream Analyze (SSE) / Phan tich tai lieu (truc tuyen)",
    tags=["Analysis"],
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "Server-Sent Events stream"},
    },
)
async def analyze_document_stream(file: UploadFile = File(...)):
    """
    Stream analysis results as Server-Sent Events.
    Each `block` event arrives as soon as a page completes — target TTFB < 1s.

    Phat truc tuyen ket qua phan tich qua SSE.
    Moi event `block` duoc day ngay khi mot trang hoan thanh — muc tieu < 1 giay.

    Event types:
    - `status` — { phase, total_pages, filename }
    - `block` — ContentBlock JSON
    - `page_done` — { page, blocks_in_page }
    - `done` — final summary { total_blocks, processing_time_ms, spatial_index, model_used }
    - `error` — { detail }
    """
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {file_ext}")

    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    temp_path = UPLOAD_DIR / safe_filename

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(413, f"File too large: max {MAX_FILE_SIZE_BYTES // (1024*1024)} MB")
    temp_path.write_bytes(content)

    async def event_generator():
        try:
            collected_blocks: list[ContentBlock] = []
            async for evt in stream_blocks_async(str(temp_path), file.filename):
                # Re-emit as SSE
                payload = json.dumps(evt["data"], ensure_ascii=False)
                yield f"event: {evt['event']}\ndata: {payload}\n\n"
                if evt["event"] == "block":
                    # Build ContentBlock for indexing later
                    collected_blocks.append(ContentBlock(**evt["data"]))
                elif evt["event"] == "done":
                    # Build full response, index into RAG, store
                    response = DocumentAnalysisResponse(
                        document_metadata=DocumentMetadata(
                            filename=file.filename or safe_filename,
                            total_pages=evt["data"]["total_pages"],
                            processing_time_ms=evt["data"]["processing_time_ms"],
                            model_used=evt["data"]["model_used"],
                        ),
                        content_blocks=collected_blocks,
                        spatial_index=SpatialIndex(**evt["data"]["spatial_index"]),
                    )
                    rag_engine = get_rag_engine()
                    rag_engine.index_document(unique_id, collected_blocks)
                    _store_analysis(unique_id, response)
                    get_tutor().register_document(unique_id, response)
                    # Tell client which doc_id to use for /query and /tts
                    yield f"event: document_id\ndata: {json.dumps({'document_id': unique_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream analysis failed: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Document-Id": unique_id,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ============================================
# UPLOAD ALTERNATIVES — URL paste + Sample library
# ============================================

class AnalyzeUrlRequest(BaseModel):
    url: str


@app.post(
    "/api/v1/analyze-url",
    response_model=DocumentAnalysisResponse,
    summary="Analyze URL — PDF, ảnh, hoặc bài viết web học liệu",
    tags=["Analysis"],
)
async def analyze_from_url(request: AnalyzeUrlRequest):
    """
    Tải nội dung từ URL công khai và phân tích.

    Hỗ trợ 3 loại:
    - PDF (application/pdf): tải binary → analyze_file_async (image-render pipeline)
    - Image (image/*): tải binary → analyze_file_async
    - HTML page (text/html): trafilatura extract main content → analyze_text_async (text-only)

    Validate chung:
    - http(s) only
    - Max 20MB
    - Timeout 30s
    - HTML article: text trích ≥ 200 chars (else reject với message giải thích)
    """
    import httpx
    from urllib.parse import urlparse

    url = request.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL phải bắt đầu bằng http:// hoặc https://")

    unique_id = uuid.uuid4().hex[:8]

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # User-Agent định danh đúng tool — tuân thủ Wikipedia/MediaWiki bot policy.
            # Các site lớn (Wikipedia, MDN) block UA giả browser ("Mozilla/...Chrome...")
            # vì coi là scraping bot. UA tool chính danh thường được phép.
            # Reference: https://meta.wikimedia.org/wiki/User-Agent_policy
            headers = {
                "User-Agent": (
                    "VisionarySTEM/2.1.0 "
                    "(educational AI reader for Vietnamese blind students; "
                    "https://github.com/anthropic-academy/visionarystem)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/pdf,image/*,*/*;q=0.8",
                "Accept-Language": "vi,en;q=0.9",
            }
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Không tải được URL: {e}")

    if len(resp.content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File quá lớn. Tối đa {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    content_type = (resp.headers.get("content-type") or "").lower()
    is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")
    is_image = content_type.startswith("image/") or any(
        url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    )
    is_html = "text/html" in content_type or "application/xhtml" in content_type

    parsed_url = urlparse(url)
    base_name = Path(parsed_url.path).name or "downloaded"

    # ============ HTML branch (NEW): trafilatura extract → analyze_text_async ============
    if is_html and not is_pdf and not is_image:
        from src.core.text_analyzer import analyze_text_async
        import trafilatura

        try:
            html_text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
        except Exception:
            html_text = resp.text

        # trafilatura.extract trả clean main content; bare_extraction trả thêm metadata
        extracted = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=True,
            include_formatting=False,
            favor_precision=True,  # ưu tiên độ chính xác (ít noise hơn)
            url=url,
        )
        # Try to get title via metadata
        try:
            metadata = trafilatura.extract_metadata(html_text, default_url=url)
            title = (metadata.title if metadata and metadata.title else "Bài viết web") if metadata else "Bài viết web"
        except Exception:
            title = "Bài viết web"

        if not extracted or len(extracted.strip()) < 200:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Không lấy được nội dung học liệu từ link. "
                    "Có thể trang yêu cầu đăng nhập, dùng JavaScript để hiển thị, "
                    "hoặc không có nội dung học. Bạn thử link khác (Wikipedia, vietjack, hocmai...) nhé."
                ),
            )

        logger.info(
            f"[analyze-url:html] {url} → extracted {len(extracted)} chars, title='{title}'"
        )

        try:
            result = await analyze_text_async(
                text=extracted,
                title=title,
                source_url=url,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"[analyze-url:html] Gemini analyze failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Phân tích text thất bại: {e}")

        # Index + register (đồng bộ với PDF flow để downstream feature hoạt động)
        rag_engine = get_rag_engine()
        rag_engine.index_document(unique_id, result.content_blocks)
        get_tutor().register_document(unique_id, result)
        _store_analysis(unique_id, result)

        body = result.model_dump()
        body["document_id"] = unique_id
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, headers={"X-Document-Id": unique_id})

    # ============ PDF / Image branch (existing) ============
    if not (is_pdf or is_image):
        raise HTTPException(
            status_code=400,
            detail=(
                f"URL không hỗ trợ (content-type: {content_type}). "
                f"Chấp nhận: PDF, ảnh, hoặc bài viết web học liệu (HTML)."
            ),
        )

    # Derive filename from URL for binary content
    if not base_name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        base_name += ".pdf" if is_pdf else ".png"

    # Save to uploads/ then analyze
    safe_filename = f"{unique_id}_{base_name}"
    temp_path = UPLOAD_DIR / safe_filename
    temp_path.write_bytes(resp.content)
    logger.info(f"[analyze-url:binary] Downloaded {len(resp.content)} bytes from {url} → {temp_path}")

    try:
        result = await analyze_file_async(file_path=str(temp_path), filename=base_name)
        rag_engine = get_rag_engine()
        rag_engine.index_document(unique_id, result.content_blocks)
        get_tutor().register_document(unique_id, result)
        _store_analysis(unique_id, result)

        body = result.model_dump()
        body["document_id"] = unique_id
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, headers={"X-Document-Id": unique_id})
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


@app.get(
    "/api/v1/library",
    summary="List sample library / Danh sach thu vien mau",
    tags=["Analysis"],
)
async def get_library():
    """Trả về metadata 6 sample documents (slug, title, description, ordinal)."""
    return {
        "items": [
            {
                "slug": item.slug,
                "title": item.title,
                "description": item.description,
                "ordinal": item.ordinal,
                "voice_aliases": item.voice_aliases,
            }
            for item in library_list_all()
        ],
        "count": len(LIBRARY),
    }


@app.post(
    "/api/v1/library/{slug}/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Load + analyze sample / Tai mau tu thu vien",
    tags=["Analysis"],
)
async def load_library_sample(slug: str):
    """Load một sample từ library + chạy analyze pipeline đầy đủ."""
    file_path = library_get_path(slug)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mẫu '{slug}' trong thư viện")

    unique_id = uuid.uuid4().hex[:8]
    try:
        result = await analyze_file_async(file_path=str(file_path), filename=file_path.name)
        rag_engine = get_rag_engine()
        rag_engine.index_document(unique_id, result.content_blocks)
        get_tutor().register_document(unique_id, result)
        _store_analysis(unique_id, result)

        body = result.model_dump()
        body["document_id"] = unique_id
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, headers={"X-Document-Id": unique_id})
    except Exception as e:
        logger.error(f"Library analyze failed for {slug}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích: {e}")


# ============================================
# SPATIAL QUERY ENDPOINTS
# ============================================

@app.post(
    "/api/v1/query",
    response_model=SpatialQueryResponse,
    summary="Spatial Voice Query / Truy van giong noi khong gian",
    tags=["Spatial Query"],
)
async def spatial_query(request: SpatialQueryRequest):
    """
    Process a natural language spatial query about a previously analyzed document.

    Xu ly truy van ngon ngu tu nhien ve khong gian cho tai lieu da phan tich.

    Example queries / Vi du truy van:
    - "Goc tren ben phai co gi?"
    - "Doc tat ca cong thuc toan"
    - "Bieu do o dau?"
    - "Phia duoi trang co noi dung gi?"
    """
    # Determine which document to query (prefer explicit, else latest)
    doc_id = request.document_id or _latest_document_id

    if not doc_id:
        raise HTTPException(
            status_code=400,
            detail="No document has been analyzed yet. Please upload a document first. / Chua co tai lieu nao duoc phan tich."
        )

    rag_engine = get_rag_engine()
    result = rag_engine.query(
        document_id=doc_id,
        query_text=request.query,
    )

    return result


# ============================================
# TTS (TEXT-TO-SPEECH) ENDPOINTS
# ============================================

@app.get(
    "/api/v1/tts/block/{block_id}",
    summary="Get Audio for Block / Lay audio cho khoi noi dung",
    tags=["TTS / Giong noi"],
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio file"},
        404: {"model": ErrorResponse, "description": "Block not found"},
    },
)
async def tts_block(
    block_id: str,
    document_id: str | None = Query(default=None),
    rate: str = Query(default="+0%", description="Speech rate, e.g. +0%, +50%, -20%"),
    pitch: str = Query(default="+0Hz", description="Speech pitch, e.g. +0Hz, +5Hz"),
):
    """Generate TTS audio for a content block. Uses content-addressed cache."""
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail="No analysis available. Analyze a document first.")

    target_block = next((b for b in last_resp.content_blocks if b.id == block_id), None)
    if target_block is None:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found.")

    try:
        path = await get_or_create_speech(target_block.spoken_text, rate=rate, pitch=pitch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    return FileResponse(path=str(path), media_type="audio/mpeg", filename=f"{block_id}.mp3")


@app.get(
    "/api/v1/tts/page/{page_number}",
    summary="Get Audio for Full Page / Lay audio cho toan trang",
    tags=["TTS / Giong noi"],
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio file"},
        404: {"model": ErrorResponse, "description": "Page not found"},
    },
)
async def tts_page(
    page_number: int = 1,
    document_id: str | None = Query(default=None),
    rate: str = Query(default="+0%"),
    pitch: str = Query(default="+0Hz"),
):
    """
    Stream MP3 audio for full page block-by-block.
    Uses StreamingResponse so client can start playing first block immediately,
    while remaining blocks are still being TTS'd.

    Phat truc tuyen audio MP3 tung khoi cho toan trang.
    """
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail="No analysis available.")

    page_blocks = [b for b in last_resp.content_blocks if b.coordinates.page == page_number]
    if not page_blocks:
        raise HTTPException(status_code=404, detail=f"No content found on page {page_number}.")
    page_blocks.sort(key=lambda b: (b.coordinates.y, b.coordinates.x))

    async def audio_chunks():
        for block in page_blocks:
            try:
                path = await get_or_create_speech(block.spoken_text, rate=rate, pitch=pitch)
                yield path.read_bytes()
            except Exception as e:
                logger.warning(f"TTS failed for {block.id}: {e}; skipping")
                continue

    return StreamingResponse(
        audio_chunks(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="page_{page_number}.mp3"'},
    )


@app.post(
    "/api/v1/tts/speak",
    summary="Speak Custom Text / Doc van ban tuy chinh",
    tags=["TTS / Giong noi"],
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio file"},
    },
)
async def tts_speak(
    text: str,
    rate: str = Query(default="+0%"),
    pitch: str = Query(default="+0Hz"),
):
    """Generate TTS for arbitrary Vietnamese text. Cached by content."""
    try:
        path = await get_or_create_speech(text, rate=rate, pitch=pitch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        filename=path.name,
    )


# ============================================
# MOCK ENDPOINT (For Person B Frontend Testing)
# ============================================

@app.get(
    "/api/v1/mock/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Mock Analysis (For Frontend Testing) / Phan tich gia lap",
    tags=["Mock / Gia lap"],
)
async def mock_analyze():
    """
    Returns a mock analysis response for frontend development.

    Loads from `tests/sample_data/mock_response.json` so the mock data can be
    edited without code changes. The JSON file contains a richer Vietnamese
    physics chapter (3 Newton laws, formulas, table, chart, examples, exercises).
    """
    mock_path = Path(__file__).resolve().parent.parent.parent / "tests" / "sample_data" / "mock_response.json"
    if not mock_path.exists():
        raise HTTPException(status_code=500, detail=f"Mock data file not found: {mock_path}")

    try:
        with mock_path.open("r", encoding="utf-8") as f:
            mock_data = json.load(f)
        mock_response = DocumentAnalysisResponse(**mock_data)
    except Exception as e:
        logger.error(f"Failed to load mock_response.json: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Mock data parse error: {e}")

    # Index mock into Spatial RAG + tutor so /query, /chat work
    rag_engine = get_rag_engine()
    rag_engine.index_document("mock_doc", mock_response.content_blocks)
    _store_analysis("mock_doc", mock_response)
    get_tutor().register_document("mock_doc", mock_response)

    # Inject document_id field for frontend (frontend reads `document_id`)
    body = mock_response.model_dump()
    body["document_id"] = "mock_doc"
    from fastapi.responses import JSONResponse
    return JSONResponse(content=body, headers={"X-Document-Id": "mock_doc"})


# ============================================
# SPRINT 8.1 — TUTOR CHAT
# ============================================

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    summary="Tutor Chat / Trò chuyện gia sư",
    tags=["Tutor (Sprint 8)"],
)
async def tutor_chat(request: ChatRequest):
    """
    Send a message to the AI tutor about a previously analyzed document.
    Maintains conversation history per session_id.

    Gửi câu hỏi tới gia sư AI về tài liệu đã phân tích.
    Lưu lịch sử hội thoại theo session_id.
    """
    last_resp = _get_analysis(request.document_id)
    if not last_resp:
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found. Analyze it first.",
        )

    tutor = get_tutor()
    # Make sure tutor knows about this document
    tutor.register_document(request.document_id, last_resp)

    try:
        return tutor.chat(
            document_id=request.document_id,
            session_id=request.session_id,
            user_message=request.message,
            voice_mode=request.voice_mode,
        )
    except Exception as e:
        logger.error(f"Tutor chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tutor error: {e}")


@app.delete(
    "/api/v1/chat/session/{session_id}",
    summary="Reset Tutor Session / Reset phiên gia sư",
    tags=["Tutor (Sprint 8)"],
)
async def reset_chat_session(session_id: str):
    """Clear conversation history for a session."""
    get_tutor().reset_session(session_id)
    return {"status": "ok", "session_id": session_id}


class ChatStreamRequest(BaseModel):
    document_id: str
    session_id: str
    message: str
    focus_block_id: Optional[str] = None


@app.post(
    "/api/v1/chat/stream",
    summary="Streaming Tutor Chat (SSE) / Truoc gia su streaming",
    tags=["Tutor (Sprint 8)"],
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE token stream"},
    },
)
async def tutor_chat_stream(request: ChatStreamRequest):
    """
    Stream tutor reply token-by-token via SSE.
    Used by Conversation page for real-time typing effect + low TTFB.

    Optional `focus_block_id`: provide context "user is listening to block_X right now".
    """
    last_resp = _get_analysis(request.document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found.")

    tutor = get_tutor()
    tutor.register_document(request.document_id, last_resp)

    async def event_generator():
        async for evt in tutor.chat_stream(
            document_id=request.document_id,
            session_id=request.session_id,
            user_message=request.message,
            focus_block_id=request.focus_block_id,
        ):
            payload = json.dumps(evt["data"], ensure_ascii=False)
            yield f"event: {evt['event']}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================
# SPRINT 8.2 — CRITIQUE LOOP
# ============================================

@app.post(
    "/api/v1/critique/{document_id}",
    response_model=DocumentAnalysisResponse,
    summary="Re-verify document blocks / Review chống hallucination",
    tags=["Critique (Sprint 8)"],
)
async def critique_document(document_id: str):
    """
    Run a second-pass critique over an already-analyzed document.
    Updates blocks in place with critique_score, needs_review, critique_issues.
    """
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    critique = get_critique()
    updated_blocks = critique.critique_blocks(document_id, last_resp.content_blocks)
    last_resp.content_blocks = updated_blocks
    _store_analysis(document_id, last_resp)
    logger.info(
        f"[critique] doc={document_id} flagged={sum(1 for b in updated_blocks if b.needs_review)}"
    )
    return last_resp


# ============================================
# SPRINT 8.3 — SONIFICATION
# ============================================

@app.get(
    "/api/v1/sonify/{block_id}",
    summary="Sonify chart block / Chuyển biểu đồ thành âm thanh",
    tags=["Sonification (Sprint 8)"],
    responses={
        200: {"content": {"audio/wav": {}}, "description": "WAV audio"},
        404: {"model": ErrorResponse, "description": "Block or document not found"},
        400: {"model": ErrorResponse, "description": "Block is not a chart"},
    },
)
async def sonify_block_endpoint(
    block_id: str,
    document_id: str | None = Query(default=None),
    duration: float = Query(default=3.0, ge=0.5, le=15.0),
):
    """
    Generate audio sonification of a chart block.
    Maps y-values → MIDI pitch, x → time. Returns WAV bytes.
    """
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail="No analysis available.")
    target = next((b for b in last_resp.content_blocks if b.id == block_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found.")
    if target.type != "chart":
        raise HTTPException(
            status_code=400,
            detail=f"Block {block_id} is type '{target.type}', not 'chart'.",
        )

    try:
        wav_bytes, _ = sonify_block(target, page_image_bytes=None, duration_s=duration)
    except Exception as e:
        logger.error(f"Sonification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sonification error: {e}")

    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={"Content-Disposition": f'inline; filename="{block_id}.wav"'},
    )


# ============================================
# SPRINT 8.4 — CAMERA LIVE
# ============================================

@app.post(
    "/api/v1/camera/snapshot",
    response_model=CameraSnapshotResponse,
    summary="Camera Live snapshot / Mô tả ảnh từ webcam",
    tags=["Camera (Sprint 8)"],
)
async def camera_snapshot(file: UploadFile = File(...)):
    """
    Quick analysis of a single camera frame (board, slide, page).
    Returns short Vietnamese description, optimized for TTS playback.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads supported.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    # Use Gemini directly with a concise prompt
    engine = get_gemini_engine()
    from google.genai import types as genai_types

    prompt = (
        "Mô tả ngắn gọn ảnh bảng/slide/trang sách này bằng tiếng Việt cho sinh viên khiếm thị. "
        "Tối đa 3 câu. Chú trọng công thức toán, biểu đồ, hoặc bảng nếu có. "
        "Trả về JSON: {spoken_text, raw_content, confidence (0-1), has_math (bool), has_chart (bool)}."
    )
    image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=file.content_type)

    try:
        response = engine.client.models.generate_content(
            model=engine.model,
            contents=[image_part, prompt],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CameraSnapshotResponse,
                temperature=0.2,
            ),
        )
        result = response.parsed
        if result is None:
            import json as _json
            result = CameraSnapshotResponse(**_json.loads(response.text))
        return result
    except Exception as e:
        logger.error(f"Camera snapshot failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Camera analyze failed: {e}")


# ============================================
# TTS V2 — GEMINI TTS (giọng tự nhiên, có cảm xúc)
# ============================================

@app.post(
    "/api/v1/tts/v2/speak",
    summary="Gemini TTS giọng cảm xúc / Natural emotional voice",
    tags=["TTS / Giong noi"],
    responses={
        200: {"content": {"audio/wav": {}}, "description": "WAV audio 24kHz mono"},
    },
)
async def tts_v2_speak(
    text: str,
    voice: str = Query(default=DEFAULT_VOICE, description=f"Voice name. Options: {', '.join(ALL_VOICES)}"),
    mood: str = Query(default="auto", description=f"Mood: auto | {' | '.join(MOOD_PRESETS.keys())}"),
):
    """
    Sinh thoại tiếng Việt bằng Gemini TTS với giọng tự nhiên + cảm xúc.

    Khác với /tts/speak (Edge TTS — robotic), endpoint này dùng Gemini 2.5 TTS:
    - 30+ voice tự nhiên, ấm áp như người thật
    - Hỗ trợ inline tag emotion: [warmly], [excitedly], [calmly]
    - Auto detect mood nếu mood=auto

    Fallback sang Edge TTS nếu Gemini lỗi/quota cạn.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text rỗng")

    actual_mood = auto_detect_mood(text) if mood == "auto" else mood

    try:
        wav_bytes = await gemini_speak_async(text, voice=voice, mood=actual_mood)
    except Exception as e:
        logger.error(f"TTS v2 failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Voice": voice,
            "X-Mood": actual_mood,
        },
    )


@app.get(
    "/api/v1/tts/v2/voices",
    summary="Liệt kê voice + mood khả dụng",
    tags=["TTS / Giong noi"],
)
async def tts_v2_voices():
    """Trả về danh sách voice và mood để UI hiển thị."""
    return {
        "voices": ALL_VOICES,
        "default_voice": DEFAULT_VOICE,
        "moods": list(MOOD_PRESETS.keys()),
        "default_mood": "warm",
    }


# ============================================
# SPRINT 6.4 — QA (single-shot Q&A, free-form)
# ============================================

class QARequest(BaseModel):
    document_id: str
    question: str


class GeneralAssistRequest(BaseModel):
    """Free-form question khi user chưa có document — assistant mode."""
    question: str
    session_id: Optional[str] = None


# In-memory conversation history per session_id cho /assist
# (giống tutor.py — Sprint 5 sẽ migrate sang DB)
# Keeps last N turns. AI sees prior greetings → không re-introduce.
_assist_sessions: dict[str, list[dict]] = {}
_ASSIST_HISTORY_MAX = 20  # cap để tránh memory leak


@app.post(
    "/api/v1/assist",
    summary="General assistant (không cần document) / General Q&A",
    tags=["Tutor (Sprint 8)"],
)
async def general_assist(request: GeneralAssistRequest):
    """
    Trả lời bất kỳ câu hỏi gì, ngay cả khi chưa tải tài liệu.

    Dùng cho:
    - Sinh viên hỏi cách dùng app: "làm sao để tải file?", "nói gì để bắt đầu?"
    - Câu hỏi STEM chung: "Niu-tơn là ai?", "Công thức vật lý cơ bản?"
    """
    engine = get_gemini_engine()
    from google.genai import types as genai_types

    system_prompt = """Bạn là VisionarySTEM, trợ lý AI tiếng Việt cho sinh viên khiếm thị.

QUY TẮC TRẢ LỜI:

1. Trả lời 100% tiếng Việt tự nhiên.

2. ❌❌❌ KHÔNG TỰ GIỚI THIỆU LẶP LẠI:
   - Nếu trong lịch sử hội thoại bạn đã giới thiệu rồi ("Chào bạn, tôi là VisionarySTEM...") →
     KHÔNG được giới thiệu lại. User đã biết bạn là ai.
   - Chỉ tự giới thiệu DUY NHẤT 1 LẦN ở câu đầu cuộc trò chuyện.
   - Lần thứ 2 trở đi, vào thẳng vấn đề user hỏi.

3. ĐỘ DÀI tuỳ ĐỘ DÀI câu user:
   - User nói NGẮN ("alo", "alo alo", "có nghe không", "hello", "ê"):
     → Reply NGẮN 1 câu duy nhất. Ví dụ: "Vâng tôi đây, bạn cần gì?" hoặc "Tôi nghe rõ, bạn nói tiếp."
   - User hỏi câu hỏi STEM hoặc cách dùng app:
     → Reply đầy đủ 3-6 câu. Mỗi câu ≤25 từ cho dễ nghe TTS.
   - ❌ KHÔNG luôn trả lời 4-7 câu cho mọi câu hỏi — quá dài cho câu chào ngắn.

4. Khi cần hướng dẫn cách dùng app:
   - Để bắt đầu: nói "Tài liệu mẫu" hoặc "Thư viện".
   - Tải tài liệu: "Tải file" (từ máy) hoặc "Tải link" (URL).
   - Khi nghe: "Tạm dừng", "Đọc tiếp", "Tua lui", "Phần này là gì".

5. NẾU user hỏi STEM (toán, lý, hoá): giải thích kèm ví dụ đời sống Việt Nam.

6. KHÔNG đọc công thức kiểu tiếng Anh: "F=ma" → "Lực bằng khối lượng nhân gia tốc".

7. ❌ KHÔNG dùng markdown bullet (*, -) hay heading (#) — TTS đọc thô.
   Thay bằng "Thứ nhất", "Thứ hai", "Một là", "Hai là".

8. KHÔNG dùng emoji, ký hiệu đặc biệt.
"""

    # Maintain in-memory conversation history per session
    sid = (request.session_id or "default").strip() or "default"
    history = _assist_sessions.setdefault(sid, [])
    history.append({"role": "user", "content": request.question})

    # Build Gemini contents from full history (so AI sees prior turns)
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=msg["content"])]))

    try:
        response = engine.client.models.generate_content(
            model=engine.model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.5,
                max_output_tokens=1200,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = (
                "Xin lỗi, tôi chưa hiểu rõ. Bạn có thể nói 'tài liệu mẫu' để bắt đầu, "
                "'tải file' để mở tài liệu, hoặc 'giúp đỡ' để nghe danh sách lệnh."
            )
        # Append assistant turn to history (for next call to see context)
        history.append({"role": "assistant", "content": reply})
        # Cap history size để tránh memory leak
        if len(history) > _ASSIST_HISTORY_MAX:
            _assist_sessions[sid] = history[-_ASSIST_HISTORY_MAX:]
        return {"reply_text": reply}
    except Exception as e:
        logger.error(f"General assist failed: {e}", exc_info=True)
        # Pop user turn — we won't reply to it
        if history and history[-1]["role"] == "user":
            history.pop()
        return {
            "reply_text": (
                "Xin lỗi, tôi đang gặp sự cố. "
                "Bạn có thể nói 'tài liệu mẫu' để bắt đầu, hoặc 'giúp đỡ' để nghe các lệnh."
            )
        }


# ============================================
# WEB SEARCH AGENT (Phase 2) — Gemini grounding với Google Search
# ============================================

class WebSearchRequest(BaseModel):
    """Request body cho /api/v1/agent/search."""
    query: str = Field(min_length=1, description="Câu hỏi/từ khoá tìm kiếm")
    max_sources: int = Field(default=5, ge=1, le=10, description="Số nguồn tối đa trả về")


@app.post(
    "/api/v1/agent/search",
    response_model=WebSearchResult,
    summary="Web search via Gemini grounding / Tim kiem qua Gemini",
    tags=["Agent (Phase 2)"],
)
async def agent_web_search(request: WebSearchRequest):
    """
    Search internet qua Gemini built-in google_search tool.

    Khác với /chat (cần document đã load) hoặc /assist (general knowledge từ training):
    endpoint này dùng Google Search để lấy thông tin THỰC TẾ HIỆN TẠI từ web.

    Use case: "tìm tài liệu chất béo hoá 12 trên mạng", "có bài tập định luật ba ở đâu".

    Trả về:
    - summary: tóm tắt tiếng Việt natural (4-7 câu)
    - sources: 3-5 nguồn được Google rank cao
    - suggested_actions: gợi ý "phân tích sâu nguồn 1", "tìm thêm chủ đề khác"

    Latency thường 5-10s (Gemini call + grounding + summarize).
    """
    try:
        result = await google_search(request.query, max_sources=request.max_sources)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[agent/search] failed for {request.query!r}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Tìm kiếm thất bại: {e}",
        )


# ============================================
# MULTI-STEP AGENT (Phase 3) — Planner + Executor SSE
# ============================================

class AgentRunRequest(BaseModel):
    """Request body cho /api/v1/agent/run."""
    request: str = Field(min_length=2, description="Yêu cầu user (câu phức tạp đa bước)")


@app.post(
    "/api/v1/agent/run",
    summary="Multi-step agent / Lap ke hoach va chay tu dong",
    tags=["Agent (Phase 3)"],
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE events"},
    },
)
async def agent_run(request: AgentRunRequest):
    """
    User yêu cầu phức tạp đa bước → Gemini planner output Plan → executor chạy
    sequential, stream SSE events cho frontend narrate progress.

    Events:
    - plan_ready: { plan_overview, steps_count, steps[] }
    - step_start: { index, narration, tool }
    - step_done: { index, summary, result_meta }
    - step_error: { index, tool, error }
    - plan_done: { summary_narration, results[] }

    Latency: planner ~3-5s + mỗi step ~5-30s tuỳ tool. Tổng ~15-60s cho 2-3 step.
    """
    try:
        plan = await make_plan(request.request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[agent/run] planner failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lập kế hoạch thất bại: {e}")

    return StreamingResponse(
        execute_plan_sse(plan),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/api/v1/qa",
    response_model=QAResponse,
    summary="Free-form Q&A on document / Hoi-dap tu do tren tai lieu",
    tags=["QA (Sprint 6)"],
)
async def doc_qa(request: QARequest):
    """
    Single-shot Q&A over an analyzed document. No conversation history.

    For multi-turn dialog, use /chat instead.
    For spatial queries ("phía dưới biểu đồ"), use /query.
    """
    last_resp = _get_analysis(request.document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found.")
    return answer_question(last_resp, request.question)


# ============================================
# SPRINT 6.1 — EPUB3 + MathML EXPORT
# ============================================

@app.get(
    "/api/v1/export/epub3/{document_id}",
    summary="Export to EPUB3 / Xuat ra EPUB3",
    tags=["Export (Sprint 6)"],
    responses={
        200: {"content": {"application/epub+zip": {}}, "description": "EPUB3 file"},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def export_epub3(document_id: str):
    """
    Export the analyzed document as EPUB3 with MathML for accessibility.
    Compatible with Thorium Reader, iBooks, Calibre, daisy-pipeline.
    """
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail="No analysis available.")

    try:
        epub_bytes = build_epub3(last_resp)
    except Exception as e:
        logger.error(f"EPUB3 build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EPUB3 export error: {e}")

    safe_name = (last_resp.document_metadata.filename or "document").rsplit(".", 1)[0]
    return StreamingResponse(
        iter([epub_bytes]),
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.epub"'},
    )


# ============================================
# SPRINT 6.2 — BRAILLE EXPORT (Unicode)
# ============================================

class BrailleRequest(BaseModel):
    text: Optional[str] = None
    latex: Optional[str] = None


class BrailleResponse(BaseModel):
    input_kind: Literal["text", "latex"]
    braille: str
    char_count: int


@app.post(
    "/api/v1/export/braille",
    response_model=BrailleResponse,
    summary="Convert text/LaTeX to Unicode Braille / Chuyen sang chu noi",
    tags=["Export (Sprint 6)"],
)
async def export_braille(request: BrailleRequest):
    """
    Convert Vietnamese text or LaTeX math to Unicode Braille (U+2800-U+28FF).

    For demo / display purposes. Production should use liblouis with vi-VN tables.
    """
    if request.latex:
        out = latex_to_braille(request.latex)
        return BrailleResponse(input_kind="latex", braille=out, char_count=len(out))
    if request.text:
        out = text_to_braille_unicode(request.text)
        return BrailleResponse(input_kind="text", braille=out, char_count=len(out))
    raise HTTPException(status_code=400, detail="Provide either 'text' or 'latex'.")


@app.get(
    "/api/v1/export/braille/{document_id}",
    summary="Export full document as Braille / Xuat toan tai lieu sang chu noi",
    tags=["Export (Sprint 6)"],
)
async def export_document_braille(document_id: str):
    """Export entire analyzed document as Unicode Braille text."""
    last_resp = _get_analysis(document_id)
    if not last_resp:
        raise HTTPException(status_code=404, detail="No analysis available.")

    lines = []
    lines.append(f"=== {last_resp.document_metadata.filename} ===")
    lines.append(text_to_braille_unicode(f"Tài liệu có {last_resp.document_metadata.total_pages} trang."))
    lines.append("")

    for b in last_resp.content_blocks:
        # Type label in Braille
        type_vi = {"text": "Văn bản", "math": "Công thức", "chart": "Biểu đồ",
                   "table": "Bảng", "figure": "Hình"}.get(b.type, b.type)
        lines.append(f"[{b.id}] {text_to_braille_unicode(type_vi)}:")
        if b.type == "math" and b.latex:
            lines.append(f"  LaTeX→Braille: {latex_to_braille(b.latex)}")
        lines.append(f"  Spoken→Braille: {text_to_braille_unicode(b.spoken_text)}")
        lines.append("")

    body = "\n".join(lines)
    safe_name = (last_resp.document_metadata.filename or "document").rsplit(".", 1)[0]
    return StreamingResponse(
        iter([body.encode("utf-8")]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.braille.txt"'},
    )


# ============================================
# Run with: uvicorn src.api.main:app --reload
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
