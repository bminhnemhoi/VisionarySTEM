---
title: VisionarySTEM Backend
emoji: 🔬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Multimodal AI for Vietnamese blind STEM students
---

# VisionarySTEM Backend API

Multimodal AI assistant cho sinh viên khiếm thị Việt Nam — đọc tài liệu STEM bằng giọng nói tự nhiên, tích hợp Gemini 2.5 Flash + spatial RAG + sonification + Braille export.

## Endpoints chính

- `GET /api/v1/health` — health check
- `POST /api/v1/analyze` — phân tích PDF/image upload
- `POST /api/v1/analyze-url` — phân tích URL (PDF/image/HTML article)
- `GET /api/v1/mock/analyze` — mock data demo (13 blocks Newton)
- `GET /api/v1/library` — list 6 sample documents
- `POST /api/v1/library/{slug}/analyze` — load + analyze sample
- `POST /api/v1/chat` — multi-turn tutor chat
- `POST /api/v1/chat/stream` — chat SSE streaming
- `POST /api/v1/assist` — general Q&A (no doc required)
- `POST /api/v1/agent/search` — web search via Gemini grounding
- `POST /api/v1/agent/run` — multi-step agent (planner + executor SSE)
- `POST /api/v1/tts/v2/speak` — Gemini Aoede TTS
- `GET /api/v1/sonify/{block_id}` — chart sonification (audio)
- `GET /api/v1/export/epub3/{doc_id}` — EPUB3 export
- `POST /api/v1/export/braille/...` — Braille Unicode export

## Configuration

Set these as **Space Secrets** (Settings → Variables and secrets):

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Get from https://aistudio.google.com/apikey |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs (vd: `https://your-app.vercel.app`) |
| `BACKEND_URL` | ✅ | Internal: `http://localhost:8000` (cùng container) |
| `GEMINI_MODEL` | ⚠️ | Default `gemini-2.5-flash` |
| `MAX_FILE_SIZE_MB` | ⚠️ | Default `20` |

## Frontend

Frontend deploy riêng trên Vercel — repo `frontend-next/`. Set env var `BACKEND_URL` của Vercel project trỏ tới URL của Space này.

## Tech Stack

- FastAPI + uvicorn (Python 3.12)
- Gemini 2.5 Flash (multimodal + TTS + grounding)
- ChromaDB (in-memory spatial RAG)
- trafilatura (HTML article extraction)
- Edge TTS (fallback)
- PyMuPDF (PDF rendering)

## License

MIT
