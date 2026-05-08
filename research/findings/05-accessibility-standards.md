# Accessibility Standards cho STEM Document AI

## TL;DR
- **MathML** = chuẩn vàng cho math accessibility (screen reader đọc được, render Braille được).
- **EPUB3 + DAISY 3** = format chuẩn cho sách accessible.
- **WCAG 2.2** (W3C) = chuẩn web accessibility, level AA bắt buộc cho B2G.
- **NIMAS** (Mỹ) = chuẩn textbook K-12 accessible.
- Output JSON của VisionarySTEM nên có thể **export sang EPUB3 + MathML** để bán cho NGO/trường.

## Vì sao quan trọng cho VisionarySTEM
- **B2B Quốc tế**: NGO accessibility (RNIB, ACB) yêu cầu output WCAG 2.2 AA + EPUB3
- **B2G**: Bộ Giáo dục VN có thể yêu cầu chuẩn quốc tế khi adopt
- **Sinh viên dùng Braille display**: cần MathML hoặc Nemeth/Marburg/LAMBDA braille code

## Thêm vào schema VisionarySTEM
```python
class ContentBlock(BaseModel):
    # ...existing...
    mathml: str | None = None         # MathML alt cho LaTeX
    nemeth_braille: str | None = None # Braille math code
    alt_text_long: str | None = None  # Mô tả dài cho figure (WCAG: alt cần concise + longdesc cho complex)
    role: str | None = None           # ARIA role: "math", "figure", "table"
```

## Pipeline export EPUB3
```
JSON content_blocks
   ├─→ HTML5 + MathML (chuẩn EPUB3)
   ├─→ DAISY 3 multimedia (sync text + audio)
   ├─→ Braille (python-louis: LaTeX→Nemeth)
   └─→ Audio book (TTS Edge → MP3)
```

## Tools tham khảo
- **python-louis** — Liblouis Braille translator (LaTeX → Nemeth)
- **MathJax** — render MathML → speech (SRE: Speech Rule Engine)
- **EPUBCheck** — validate EPUB3 output
- **Ace by DAISY** — validate accessibility
- **ChattyInfty** — DAISY math tool tham khảo UX

## Sources
- [DAISY MathML Spec](https://daisy.org/activities/standards/daisy/mathml/mathml-in-daisy-specification/)
- [DAISY Wikipedia](https://en.wikipedia.org/wiki/Digital_Accessible_Information_System)
- [DO-IT Accessible Math Textbooks](https://www.washington.edu/doit/how-can-publishers-create-accessible-math-textbooks)
- [MIT Umwelt — accessible charts](https://news.mit.edu/2024/umwelt-enables-interactive-accessible-charts-creation-blind-low-vision-users-0327)
- [AI for Accessible Education arXiv](https://arxiv.org/html/2504.17117v1)

## Key papers cần đọc
- "Building Multimodal Chart Accessibility for Blind and Low-Vision Individuals in the Prompt-Driven Era" (ACM XRDS) — input cho chart description
- "Screen Reader AI: Conversational Web-Accessibility Assistant" (IJESTY) — UX inspiration
- ASSETS conference proceedings (mỗi năm) — go-to venue cho accessibility AI
