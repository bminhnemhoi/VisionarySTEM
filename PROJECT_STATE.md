# VisionarySTEM - PROJECT STATE

> **Last Updated:** 2026-04-28 (Sprint 5+6 added)
> **Current Phase:** Sprint 1-9 + 5.6-5.7 + 6.1-6.4 COMPLETED → Production-ready MVP
> **Plan**: `C:/Users/Admin/.claude/plans/tri-n-khai-d-n-peaceful-star.md`
> **Research library**: 14 findings markdown + 9 repos clone
> **Tests**: 98/98 passed, 73% coverage
> **Backend**: API 2.1.0 — **17 endpoints** (analyze + stream, query, tts×3, mock, chat×2, critique, sonify, camera, **qa**, **epub3**, **braille×2**)
> **Frontend**: Next.js 14 — **5 pages** (`/`, `/workspace`, `/tutor`, `/live`, `/pricing`) + 3 themes + keyboard shortcuts (`?`, `g+letter`)
> **Legal**: TOS, Privacy Policy, Accessibility Statement đã viết (`docs/`)

---

## CURRENT STATUS

### Phase 1: Foundation - DONE
- Gemini 2.5 Flash engine with structured JSON output
- FastAPI with /health, /analyze, /mock/analyze
- Bilingual docs (EN/VI): README, API Contract, Architecture
- PyMuPDF PDF processing pipeline
- Edge TTS Vietnamese voice engine

### Phase 2: Spatial RAG + TTS Integration - DONE
- **Spatial RAG** (`src/core/spatial_rag.py`):
  - ChromaDB in-memory vector store
  - Vietnamese keyword-based region detection (9 regions)
  - Content type filtering (math, chart, table, figure, text)
  - Natural Vietnamese spoken answer generation
- **TTS API Endpoints**:
  - `/api/v1/tts/block/{block_id}` - Audio for single block
  - `/api/v1/tts/page/{page}` - Full page audio (per-block concat)
  - `/api/v1/tts/speak` - Custom text speech
- **Spatial Query Endpoint**:
  - `POST /api/v1/query` - Natural language spatial queries
  - Auto-indexes analysis results into ChromaDB
- **All 23/23 integration tests PASSED**

### Phase 3: Evaluation & Optimization - DONE
- **Latency Optimization** (`src/core/document_processor.py`):
  - PyMuPDF inline rendering (1500px, JPEG 85 compression).
  - Reduced payload size from ~3MB to ~150KB.
  - Bypassed intermediate Google Cloud Files Upload APIs in favor of High-Speed Inline Base64 Data API.
- **WER Benchmark System** (`src/evaluation/wer_calculator.py`):
  - `jiwer` Character Error Rate (CER) and WER analysis.
  - Robust bounding mapping using lowest CER indexing.
  - **Results**: Math WER = 0.0% (Perfect formulation).

### Tech Stack
- **AI Model:** Gemini 2.5 Flash (google-genai SDK)
- **Backend:** FastAPI v2.0.0
- **Frontend:** Streamlit (Person B)
- **TTS:** Edge TTS (vi-VN-HoaiMyNeural)
- **Vector DB:** ChromaDB (in-memory)
- **Evaluation:** Jiwer (WER/CER metrics)
- **API Key:** Managed in .env (gitignored)

---

## API ENDPOINTS (8 total)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/health | Health check |
| POST | /api/v1/analyze | Real Gemini analysis + auto-index |
| POST | /api/v1/query | Spatial voice queries |
| GET | /api/v1/tts/block/{id} | Block audio |
| GET | /api/v1/tts/page/{page} | Full page audio |
| POST | /api/v1/tts/speak | Custom text speech |
| GET | /api/v1/mock/analyze | Mock data for Person B |

---

## SPRINT 1 P0 FIXES - DONE 2026-04-27

- [x] Đồng bộ model name về `gemini-2.5-flash` trên README, AI_RULES, api_contract, architecture, gemini_engine, mock JSON
- [x] CORS: thay `["*"]` bằng `ALLOWED_ORIGINS` env var (default localhost:8501,3000)
- [x] Replace deprecated `@app.on_event("startup")` bằng `lifespan` async context manager
- [x] Refactor `_last_analysis` global dict → `_analyses[doc_id]` + `_latest_document_id` fallback
- [x] Endpoint `/query`, `/tts/block/{id}`, `/tts/page/{n}` nhận `document_id` query param
- [x] `/analyze` trả về `X-Document-Id` header + `document_id` field trong body
- [x] Xóa dead code Files API path trong `gemini_engine.GeminiEngine.analyze_document()` (~100 dòng)
- [x] Fix `sys.exit(1)` lúc import → `MissingApiKeyError` raise lazy qua `require_api_key()`
- [x] API version bump 2.0.0 → 2.0.1
- [x] Tạo `research/` library với 10 findings markdown + INDEX
- [x] `.gitignore` exclude research artifacts nặng

## SPRINT 2 - Performance & Reliability - DONE 2026-04-27

- [x] **Async parallel pages**: `analyze_file_async()` với `asyncio.gather` + `Semaphore(MAX_CONCURRENT_PAGES=4)` — multi-page PDF giảm từ 19s sequential xuống ~T_max + overhead
- [x] **Streaming SSE endpoint**: `POST /api/v1/analyze/stream` đẩy events `status`, `block`, `page_done`, `done`, `document_id` ngay khi page xong (target TTFB <1s)
- [x] **TTS cache**: hash-based MP3 cache trong `output/tts_cache/` (sha1 của voice|rate|pitch|text); endpoint TTS thêm `?rate=+50%&pitch=+5Hz` cho accessibility
- [x] **TTS streaming**: `/tts/page/{n}` dùng `StreamingResponse` — client phát ngay block đầu trong khi block sau còn TTS'd
- [x] **Spatial RAG RELATION_KEYWORDS**: implement thực sự `_detect_relation()` + `_apply_relation_filter()` cho queries "phía dưới biểu đồ", "phía trên công thức", "bên trái bảng"...
- [x] **Persistent ChromaDB**: `SpatialRAGEngine(persist_dir=...)` hoặc env `CHROMA_PERSIST_DIR` → `PersistentClient` (sống qua restart)
- [x] **WER Hungarian matching**: `scipy.optimize.linear_sum_assignment` thay greedy CER → ghép GT↔AI tối ưu toàn cục, đếm `unmatched_gt` và `extra_ai` riêng biệt
- [x] **pytest suite**: 49 tests, **73% coverage** (`tests/test_{schemas,helpers,wer_calculator,spatial_rag,api,document_processor}.py`)
- [x] **GitHub Actions CI**: `.github/workflows/ci.yml` chạy ruff + pytest trên Python 3.11 & 3.12, upload coverage Codecov
- [x] **pyproject.toml**: pytest config, ruff config, coverage config

## SPRINT 3 - Frontend + Demo - DONE 2026-04-27

- [x] **Frontend Streamlit** (`frontend/app.py` + `frontend/utils/api_client.py` + `frontend/utils/pdf_renderer.py`)
- [x] **High-contrast theme** (`frontend/styles/high_contrast.css`) — đen/vàng, font ≥18px, click target ≥50px, WCAG AAA contrast 7:1+, skip-link, keyboard hints
- [x] **SSE streaming client** đọc `event:` + `data:` từ `/analyze/stream`, hiển thị block tăng dần
- [x] **PDF viewer + bounding box overlay** với màu theo type, highlight selected block
- [x] **Voice query UI**: text input + `streamlit-mic-recorder` (optional dependency) + auto-play TTS câu trả lời
- [x] **TTS rate/pitch slider** trong sidebar — accessibility critical (người khiếm thị thích nghe +50%-100%)
- [x] **Demo storyboard 3 phút** (`docs/demo_storyboard.md`) — kịch bản chi tiết 5 đoạn cho cuộc thi
- [x] **Slide outline 15 slide** (`docs/SLIDE_OUTLINE.md`) — title, problem, solution, demo, architecture, USP, metrics, accessibility, competitors, business model, tech stack, roadmap, scientific contribution, team, Q&A
- [x] **5 PDF mẫu mở rộng**: calculus, linear algebra, chemistry, statistics, wave physics + 5 ground-truth JSON
- [x] **Benchmark suite** (`scripts/run_benchmark.py`) — chạy tất cả 6 PDFs, output bảng so sánh

## SPRINT 4 - Multi-tenant Foundation - DONE 2026-04-27

- [x] **Schema extensions** (`src/api/schemas.py`): `reading_order`, `importance`, `alt_text_long`, `mathml`, `parent_id`, `aria_role` — tất cả Optional → backward-compat 100%
- [x] **Auth/Tenant module** (`src/auth/tenant.py`): `TenantContext` + `get_tenant_context` + `require_tenant` dependencies. Single-mode trả default tenant với admin role; multi-mode parse JWT claims hoặc X-Tenant-Id header
- [x] **DB models SQLAlchemy 2.0** (`src/db/models.py`): 6 tables (`tenants`, `users`, `documents`, `content_blocks`, `usage_logs`, `subscriptions`) với indexes + denormalized `tenant_id` cho RLS perf
- [x] **DB session** (`src/db/session.py`): async session với `SET LOCAL app.tenant_id` trong transaction
- [x] **RLS template** (`RLS_SQL_TEMPLATE` trong models.py) — sẽ apply qua Alembic migration trong Sprint 5
- [x] **docker-compose.yml**: Postgres 16 + Redis 7 + MinIO + healthchecks + volumes; `scripts/db_init.sql` tạo `vs_app` user (RLS enforce) tách khỏi migration user
- [x] **Dockerfile** production: multi-stage, non-root user, healthcheck, 2 workers
- [x] **.dockerignore** loại trừ tests/research/docs khỏi image
- [x] **Tests mở rộng**: `test_auth.py` (4 tests), `test_schema_extensions.py` (3 tests) → tổng 56/56 pass

## SPRINT 7 - Frontend Next.js + Friendly Education UI - DONE 2026-04-28

- [x] **Next.js 14 + TypeScript + Tailwind + Radix primitives** trong `frontend-next/`
- [x] **3-theme system**: friendly-light (default), friendly-dark, high-contrast (WCAG AAA)
- [x] **Pages**: `/` (marketing hero + features), `/workspace` (analyze + SSE + spatial query), `/tutor`, `/live`
- [x] **shadcn/ui-style primitives**: Button, Card, Badge, Progress, Tabs, Tooltip, ScrollArea, Sonner Toaster, Separator
- [x] **API proxy** Route Handler `/api/proxy/[...path]` ẩn backend URL + tránh CORS, support streaming SSE
- [x] **Custom AudioPlayer** với progress bar + ARIA + autoplay
- [x] **Theme switcher** (3 modes) persist localStorage
- [x] **Skip link** + topbar + footer accessible
- [x] **Workspace UI**: Upload dropzone với drag-drop, SSE streaming progress, block list với critique badge + sonify button cho chart, regions tab, voice query với suggested prompts

## SPRINT 8 - Netra Edu Features - DONE 2026-04-28

- [x] **8.1 Tutor multi-turn chat** (`src/core/tutor.py`):
  - `TutorEngine` với conversation history per session
  - System prompt scaffolding cho gia sư STEM tiếng Việt
  - Endpoint `POST /api/v1/chat` + `DELETE /api/v1/chat/session/{id}`
  - Auto cite blocks + suggested followups
  - Frontend: `components/tutor/chat-panel.tsx` với bubble UI, follow-up chips, auto TTS reply
- [x] **8.2 Critique loop** (`src/core/critique.py`):
  - `CritiqueEngine` 2nd-pass review (LaTeX validity, spoken_text accuracy, type consistency)
  - Confidence merging: 0.6 * gemini + 0.4 * critique
  - Endpoint `POST /api/v1/critique/{document_id}`
  - Frontend: badge ⚠️ "Cần xem lại" + expandable issues list
- [x] **8.3 Sonification** (`src/core/sonification.py`):
  - Chart data extraction qua Gemini → JSON points
  - WAV generation: y-values → MIDI pitch (C4-C6), x → time, attack/release envelope, reference tick
  - Endpoint `GET /api/v1/sonify/{block_id}?duration=3.0`
  - Frontend: nút 🎵 "Nghe biểu đồ" trên chart blocks
- [x] **8.4 Camera Live mode** (endpoint `POST /api/v1/camera/snapshot`):
  - Quick analyze single image (3-câu mô tả tiếng Việt)
  - Returns `{spoken_text, raw_content, confidence, has_math, has_chart}`
  - Frontend: `components/camera/live-capture.tsx` với getUserMedia + auto interval 3-10s + history panel
- [x] **8.6 Tests**: 20 tests mới (7 sonification + 6 tutor + 7 critique) — **76/76 pass**, coverage 73%

## SPRINT 9 - Research Library Expansion - DONE 2026-04-28

- [x] 4 findings markdown mới:
  - `11-tutor-ai-accessibility.md` — Dialog scaffolding, pedagogy patterns
  - `12-sonification-tactile.md` — MIT Umwelt, MIDI mapping algorithm
  - `13-multiagent-edu.md` — AutoGen/CrewAI/LangGraph + MA-LED Belief Construction
  - `14-vn-accessibility-ecosystem.md` — Trường NĐC, EDUi, Sở GD/KHCN, pricing VN, GTM 12 tháng
- [x] 3 repos clone mới: `tools/autogen`, `tools/crewai`, `tools/langgraph`
- [x] `findings/INDEX.md` cập nhật

## NEXT STEPS

### Còn lại của plan
- **Sprint 5** (Productization): Alembic migrations, Paddle/PayOS billing, Auth UI, Admin dashboard, quota enforcer (3-4 ngày)
- **Sprint 6** (Innovation Round 2): EPUB3 + Braille export, VN-STEM-50 dataset (3-5 ngày)

### Hành động ngay
1. `cd frontend-next && npm install && npm run dev` — test UI mới
2. So sánh UX Streamlit (`frontend/`) vs Next.js (`frontend-next/`) — chọn primary
3. Quay video demo theo `docs/demo_storyboard.md` (đã có) bằng Next.js UI
4. Apply Microsoft AI for Good grant + liên hệ Trường Nguyễn Đình Chiểu

## ⚠️ ACTION REQUIRED FROM USER

- **Rotate Gemini API key**: key trong `.env` đã bị lộ trong session AI (chưa bao giờ commit git, nhưng nên rotate ngay tại https://aistudio.google.com/apikey)

---

> **Note for AI:** Read this file, `AI_RULES.md`, and `research/findings/INDEX.md` first when resuming work.
