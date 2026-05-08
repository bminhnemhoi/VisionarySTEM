# VisionarySTEM – Research & Reference Library
# Thư viện Nghiên cứu & Tham chiếu

> Folder này chứa tài liệu khảo sát, tải về, và tổng hợp về các công nghệ/nghiên cứu liên quan tới VisionarySTEM.
> **Luôn tham chiếu folder này** khi cần ý tưởng, baseline, hay best-practice.

## Cấu trúc

```
research/
├── papers/                  # Bài báo PDF tải về (arXiv, ACL, CVPR, ASSETS, ...)
├── tools/                   # Code/repo tham khảo (clone shallow, demo notebook)
├── benchmarks/              # Datasets + leaderboards (MathVista, ViDoRe, OmniDocBench)
├── competitors/             # Phân tích sản phẩm cạnh tranh (Bookshare, BeMyEyes, Seeing AI…)
├── vietnamese-nlp/          # Tài nguyên tiếng Việt: PhoWhisper, VietTTS, VnCoreNLP…
├── accessibility-standards/ # WCAG 2.2, EPUB3, DAISY, MathML, NIMAS
├── saas-architecture/       # Multi-tenant patterns, billing VN, auth flows
└── findings/                # Markdown tổng hợp từ web research + ghi chú
```

## Quy tắc
- File >50MB không commit vào git — đã thêm vào `.gitignore` của research/
- Mỗi paper khi lưu PDF, đi kèm 1 file `{paper-slug}.notes.md` có 5 dòng tóm tắt
- Mỗi tool clone đi kèm `WHY_USEFUL.md` ngắn gọn (≤ 100 từ) giải thích lý do tham chiếu
- Cập nhật `findings/INDEX.md` khi thêm tài liệu mới

## Last update
Khởi tạo: 2026-04-27 — Cuộc thi TDTU Vibe Coding 2026 + thương mại hoá song song.
