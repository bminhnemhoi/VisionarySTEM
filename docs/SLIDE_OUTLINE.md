# 🎯 Slide Thuyết Trình VisionarySTEM (10-15 slide, 7 phút)

> Format: Google Slides hoặc PowerPoint, 16:9, accessibility-friendly.
> Theme: dark background (#0a0a0a) + accent #ffd600 (như UI app).

---

## Slide 1 — Title

```
🔬 VisionarySTEM
Multimodal AI Agent cho Sinh viên Khiếm thị STEM

TDTU Vibe Coding 2026
Team: [Tên A] (Backend), [Tên B] (Frontend)
```

---

## Slide 2 — Vấn đề (Problem)

**Tiêu đề**: 60,000 sinh viên khiếm thị Việt Nam gặp rào cản với STEM

**Bullet**:
- 📉 Screen reader đọc `F = ma` → "F equals m a" (vô nghĩa)
- 🚫 PDF có công thức + biểu đồ → 0% accessibility
- ⏰ Sinh viên phụ thuộc bạn bè đọc giúp → mất 3-5h/ngày
- 🌍 Không có tool nào tiếng Việt cho STEM

**Hình**: photo sinh viên khiếm thị + biểu đồ thống kê.

---

## Slide 3 — Giải pháp (Solution)

**Tiêu đề**: VisionarySTEM = Gemini multimodal + Vietnamese spoken text + Spatial RAG

**Mô hình 3 bước**:
```
PDF/Ảnh → Gemini 2.5 Flash → JSON cấu trúc → TTS tiếng Việt
                              ↓
                        Spatial RAG → Voice query
```

**Điểm nhấn**:
- 100% spoken_text **tiếng Việt tự nhiên**
- Math: `F = ma` → "Lực bằng khối lượng nhân gia tốc"
- Spatial query: "Phía dưới biểu đồ có gì?" → trả lời thông minh

---

## Slide 4 — Demo Video (3 phút)

[Embed link demo video — xem `docs/demo_storyboard.md`]

---

## Slide 5 — Kiến trúc (Architecture)

Diagram từ `docs/architecture.md`:
- Frontend Streamlit (theme tương phản cao)
- Backend FastAPI (9 endpoints + SSE streaming)
- Gemini 2.5 Flash (multimodal)
- ChromaDB (Spatial RAG with persistent option)
- Edge TTS (vi-VN-HoaiMyNeural) + cache

---

## Slide 6 — Đột phá kỹ thuật

**3 USP cốt lõi**:

1. **Streaming SSE** — TTFB < 1s, latency 19s → 2.8s (6× nhanh hơn)
2. **Spatial RAG với 5 quan hệ không gian** — chưa thấy sản phẩm nào làm
   - above / below / left_of / right_of / next_to
   - Anchor detection: "dưới biểu đồ" → tìm chart anchor
3. **Vietnamese-first TTS** — rate +50% cho người khiếm thị

---

## Slide 7 — Số liệu (Metrics)

**Bảng kết quả**:

| Metric | Target | Actual |
|--------|--------|--------|
| Math WER | < 5% | **0.0%** ✅ |
| Text WER | < 10% | **8.4%** ✅ |
| Latency p95 | < 5s/page | **2.8s** ✅ |
| TTFB streaming | < 1s | **0.8s** ✅ |
| Test coverage | ≥ 70% | **73%** ✅ |
| Endpoints | 8+ | **9** ✅ |

**Nguồn**: `benchmark_report.md` + `pytest --cov=src`

---

## Slide 8 — Tính năng dành cho khiếm thị (Accessibility)

- ✅ Theme tương phản cao (đen #0a0a0a + vàng #ffd600), WCAG AAA contrast 7:1+
- ✅ Font tối thiểu 18px
- ✅ Click target ≥ 50px (WCAG AAA)
- ✅ Skip link cho screen reader
- ✅ Keyboard shortcuts đầy đủ (Tab, Enter, Space, ↑↓, Esc)
- ✅ TTS rate / pitch tuỳ chỉnh
- ✅ Auto-play câu trả lời voice query

---

## Slide 9 — So sánh đối thủ

| Sản phẩm | VN | Math TTS | Spatial Query | Multi-tenant |
|----------|----|----|---------------|--------------|
| **VisionarySTEM** | ✅ | ✅ | ✅ | ✅ ready |
| Be My Eyes (BeMyAI) | ⚠️ partial | ⚠️ | ❌ | ✅ |
| Microsoft Seeing AI | ❌ | ❌ | ❌ | ❌ |
| Bookshare | ❌ | ✅ EPUB | ❌ | ✅ |
| Mathpix | ❌ | ❌ no TTS | ❌ | ✅ |

**Định vị**: "Bookshare cho người Việt nhưng tự động hoá bằng AI"

---

## Slide 10 — Mô hình kinh doanh (Business Model)

**4 segment khách hàng**:

1. **B2B Đại học VN** — $200-2000/tháng/seat (TDTU, ĐHQG, HUS)
2. **B2C Sinh viên** — Free tier + Pro 99k VNĐ/tháng
3. **B2G NGO + Bộ GD** — Grant/CSR (Microsoft AI for Good)
4. **B2B Quốc tế** — RNIB Anh, ACB Mỹ ($1k-10k/tháng)

**TAM**: ~285M USD (Vietnam EdTech accessibility 2026, Mordor Intelligence)

**Pricing model**:
- Pay-per-page (1k VNĐ/page) cho Free
- Subscription cho Pro/Enterprise
- White-label cho B2B Quốc tế

---

## Slide 11 — Tech Stack

**Bilingual stack**:

| Layer | Tech |
|-------|------|
| AI Core | Gemini 2.5 Flash (+ Mathpix/PhoWhisper khi cần) |
| Backend | FastAPI + Pydantic + ChromaDB + Edge TTS |
| Frontend | Streamlit + streamlit-mic-recorder + Pillow |
| Storage | Cloudflare R2 / MinIO local |
| Auth | Supabase Auth (multi-tenant ready) |
| Payment | Paddle (global) + PayOS (VN) |
| CI | GitHub Actions, ruff + pytest 73% cov |

---

## Slide 12 — Roadmap

**6 Sprint, 15-20 ngày**:

- ✅ **Sprint 0** — Research library (10 findings + 6 repos clone)
- ✅ **Sprint 1** — P0 fixes (security, doc sync, CORS)
- ✅ **Sprint 2** — Performance (SSE streaming, async parallel, 73% test cov)
- ✅ **Sprint 3** — Frontend Streamlit + Demo
- 🔜 **Sprint 4** — Multi-tenant SaaS (Postgres RLS, Auth)
- 🔜 **Sprint 5** — Productization (Billing Paddle/PayOS, Admin UI)
- 🔜 **Sprint 6** — Innovation (EPUB3 + Braille export, Voice-first UX)

---

## Slide 13 — Đóng góp khoa học

**Outputs khả dĩ**:

1. **Dataset VN-STEM-50** — 50 trang STEM tiếng Việt + ground-truth → public
2. **Paper ASSETS 2026** — "Spatial RAG for Vietnamese Math Document Accessibility"
3. **Open-source release** — code MIT + hướng dẫn re-train cho ngôn ngữ khác
4. **Workshop tại HỘI Người Mù VN** — chuyển giao công nghệ

---

## Slide 14 — Team & Cảm ơn

**Person A (Backend)**: AI pipeline, Gemini, RAG, FastAPI
**Person B (Frontend)**: Streamlit, voice UX, accessibility CSS

**Mentors**: [Tên thầy/cô]

**Tools used**:
- Claude Code, Cursor IDE
- Google Gemini 2.5 Flash
- VinAI PhoWhisper, ColPali, Marker

---

## Slide 15 — Q&A + Contact

```
🌐 GitHub:        github.com/[team]/VisionarySTEM
📧 Email:         visionarystem@[domain]
🎙 Demo live:     vs-demo.[domain]
📄 Whitepaper:    [link PDF]

Cảm ơn ban giám khảo Vibe Coding 2026 ❤️
```

---

## 🎨 Design notes

- Mỗi slide: ≤ 6 dòng text, font ≥ 28pt
- Color: bg #0a0a0a, text #f5f5f5, accent #ffd600
- Icons: emoji (universal) hoặc Heroicons SVG
- Animation: fade-in cơ bản, KHÔNG dùng spin/bounce gây mệt mắt
- Backup: bản PDF không animation cho giám khảo tải về
