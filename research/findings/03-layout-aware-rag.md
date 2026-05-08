# Layout-Aware RAG cho Document AI (April 2026)

## TL;DR
- **ColPali / ColQwen2** = SOTA cho visual document RAG, không cần OCR.
- **LAD-RAG** (arXiv 2510.07233) — Layout-Aware Dynamic RAG: xây document graph + neural embedding song song.
- **SuperRAG** (NAACL 2025) — Layout-aware graph modeling cho DocVQA.
- ColQwen2-2B/7B là default cho production 2025-2026.

## So với current Spatial RAG của VisionarySTEM
| Hiện tại | Đề xuất nâng cấp |
|----------|------------------|
| ChromaDB + sentence-transformers default | ColQwen2 multi-vector embedding |
| Keyword Vietnamese region detection | Giữ keyword (rẻ) + thêm visual patch retrieval |
| In-memory, mất khi restart | PersistentClient + per-tenant collection |
| Embed `spoken_text + raw_content` | Embed cả image patch của block (multi-modal) |

## Kiến trúc đề xuất hybrid
```
User query
   ├─→ Intent classifier (Gemini Flash)
   │     ├─ Region query → keyword filter (REGION_KEYWORDS giữ nguyên)
   │     ├─ Type query → metadata filter (math/chart/...)
   │     ├─ Semantic query → ColQwen2 visual retrieval
   │     └─ Spatial relation ("dưới biểu đồ") → graph traversal (LAD-RAG style)
   ├─→ Top-K results merge
   └─→ Spoken answer generator (Gemini Flash)
```

## Code/repo cần clone
- `git clone https://github.com/illuin-tech/colpali tools/colpali` — code chính thức
- ColQwen2 weights từ HF: `vidore/colqwen2-v1.0`
- LAD-RAG paper: arXiv 2510.07233 → `papers/`

## Vấn đề cần lưu ý
- ColQwen2 cần GPU để inference nhanh — không phù hợp on-device
- Embedding storage size lớn (multi-vector) — cần Vespa/Qdrant cho scale
- Cho VN STEM, cần fine-tune trên doc tiếng Việt nếu retrieval kém

## Sources
- [ColPali repo](https://github.com/illuin-tech/colpali)
- [LAD-RAG arXiv](https://arxiv.org/abs/2510.07233)
- [SuperRAG NAACL 2025](https://aclanthology.org/2025.naacl-industry.45.pdf)
- [Visual RAG Toolkit](https://arxiv.org/html/2602.12510)
- [Mixpeek Visual Doc Retrieval](https://mixpeek.com/visual-document-retrieval)
