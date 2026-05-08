# SOTA PDF & Math Formula Extraction (April 2026)

## TL;DR
- **Marker-pdf** (VikParuchuri) là SOTA open-source cho parse PDF → Markdown với chế độ `--use_llm` cho math/table chính xác hơn.
- **Surya / Texify** đã merge: dùng `surya_latex_ocr` cho math OCR.
- **Nougat** (Meta) tốt cho cả trang nhưng hallucinate trên ảnh nhỏ chỉ chứa math.
- **OmniDocBench** (CVPR 2025) là benchmark đánh giá thống nhất nhiều parser.
- **Mathpix** vẫn là gold-standard commercial nhưng đắt — chỉ dùng cho công thức siêu phức tạp khi Gemini fail.

## So sánh nhanh
| Tool | Open-source | Math | Table | Layout | Tiếng Việt |
|------|-------------|------|-------|--------|-----------|
| Marker-pdf v2 | ✅ | Tốt (LLM mode) | Tốt | Tốt | OK |
| Surya / Texify | ✅ | Rất tốt | Tốt | OK | Hạn chế |
| Nougat | ✅ | Tốt | Trung bình | Trung bình | Kém |
| Gemini 2.5 Flash native | ❌ paid | Tốt | Khá | Khá (cần prompt) | Tốt |
| Mathpix | ❌ paid | Xuất sắc | Xuất sắc | Xuất sắc | OK |
| ColPali / ColQwen2 (visual RAG) | ✅ | Không OCR — chỉ retrieval | – | Patch-level | – |

## Khuyến nghị áp dụng cho VisionarySTEM
1. **Giữ Gemini 2.5 Flash làm backbone**: chính sách AI_RULES.
2. **Thêm Marker-pdf làm pre-processor optional** (`--use_llm=false`): chiết LaTeX cấp khối nhanh, đối chiếu với Gemini → tăng độ chính xác math.
3. **Mathpix làm fallback cao cấp** cho công thức phức tạp khi `confidence < 0.85` (chỉ trả phí khi cần).
4. **Surya cho ảnh đơn lẻ** (không qua PDF): nhanh hơn upload Gemini.
5. **Benchmark theo OmniDocBench**: tự tạo subset tiếng Việt 50 trang STEM → so sánh các tool.

## Điều cần download/clone
- `git clone https://github.com/VikParuchuri/marker.git tools/marker` — shallow
- `git clone https://github.com/VikParuchuri/surya.git tools/surya` — shallow
- Download paper "Benchmarking Document Parsers on Mathematical Formula Extraction" (arXiv 2512.09874) → `papers/`
- Download OmniDocBench paper (CVPR 2025) → `papers/`

## Sources
- [OmniDocBench CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.pdf)
- [Math Formula Extraction Benchmark](https://arxiv.org/abs/2512.09874)
- [marker-pdf](https://pypi.org/project/marker-pdf/)
- [texify (now in surya)](https://github.com/VikParuchuri/texify)
- [DocTron-Formula](https://arxiv.org/pdf/2508.00311)
