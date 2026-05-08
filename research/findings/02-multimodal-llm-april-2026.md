# Multimodal LLM Landscape (April 2026)

## TL;DR
- **Gemini 3.1 Pro** dẫn đầu MathVista, MMMU, document understanding.
- **Claude Opus 4.6** mạnh về reasoning + code, OK về vision.
- **GPT-5.4** cân bằng nhất, tốt về tool-use.
- **Meta Muse Spark** mới ra, vision-first.
- 3 model top-tier giờ "ngang ngửa" trên benchmark thuần — chọn theo workload, ko phải accuracy.

## Khuyến nghị routing cho VisionarySTEM
| Task | Model lựa chọn | Lý do |
|------|----------------|-------|
| Phân tích trang STEM (chính) | **Gemini 2.5 Flash** | Rẻ, đủ tốt, latency thấp |
| Trang siêu phức tạp (>0.85 confidence cần thiết) | Gemini 3.1 Pro | Best multimodal, đắt hơn |
| Math hard reasoning (giải bài tập) | Claude Opus 4.6 | Reasoning xuất sắc |
| QA về tài liệu (tooluse + retrieval) | GPT-5.4 hoặc Gemini Flash | Tool-use ngon |
| Voice query intent classification | Gemini Flash 2.5 (rẻ) | Ko cần phức tạp |

## Tích hợp multi-provider (đã được user chấp thuận)
Cần lớp **Model Router** có:
- Provider abstraction (Gemini, Anthropic, OpenAI)
- Cost & latency tracking per call
- Fallback chain: Gemini Flash → Gemini Pro → Claude → manual review
- A/B test framework để đo accuracy thực tế

## Mathvista benchmark hiện tại (April 2026)
- Gemini 3.1 Pro: ~78% (lead)
- Claude Opus 4.6: ~74%
- GPT-5.4: ~72%
- (số liệu approx, cần confirm)

## Sources
- [LLM Council Apr 2026](https://lmcouncil.ai/benchmarks)
- [LumiChats comparison](https://lumichats.com/blog/gemini-3-1-pro-vs-claude-sonnet-46-vs-gpt-54-april-2026-real-comparison)
- [Vellum LLM Leaderboard 2026](https://www.vellum.ai/llm-leaderboard)
- [MathVista](https://mathvista.github.io/)
