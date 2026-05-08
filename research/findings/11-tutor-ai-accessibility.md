# Tutor AI cho Người Khiếm thị (CHI/ASSETS 2024-2026)

## TL;DR
- **Khoảng trống lớn**: Hầu hết tools (Seeing AI, Be My AI, VisionPal) chỉ "**mô tả**" chứ chưa "**dạy**". Cần dialog scaffolding kiểu tutor.
- **Pattern khuyến nghị**: System prompt định vị rõ "bạn là gia sư", có conversation history, suggest follow-up prompts, cite back to source blocks.
- **Tránh hallucination**: Critique loop (Sprint 8.2) hoặc multi-agent verification.
- **VN-specific**: Chưa tool nào làm tutor STEM tiếng Việt → market trống hoàn toàn.

## Patterns từ paper SOTA

### 1. Dialog Scaffolding (CHI/ASSETS pattern)
Trợ lý AI tốt cho khiếm thị phải:
1. **Bắt đầu bằng tóm tắt** (overview) — "Trang này có 5 phần: tiêu đề, nội dung, công thức..."
2. **Cho phép drill-down** ("Đọc kỹ phần công thức")
3. **Suggest follow-ups** ngắn ("Bạn muốn ví dụ cụ thể không?", "Giải thích đơn giản hơn?", "Kiểm tra hiểu biết?")
4. **Cite source** — luôn link câu trả lời về block ID đã phân tích, để user verify lại

### 2. Pedagogical Strategies cho Blind Learners
Nghiên cứu (AI for Accessible Education, arXiv 2504.17117) chỉ ra:
- **Audio-first**: trả lời ưu tiên cấu trúc tuần tự (vì không có visual scan-back)
- **Concrete examples > abstract**: thay vì "F = ma là định luật cơ bản" → "Hãy tưởng tượng đẩy xe chở đồ: lực bạn đẩy quyết định xe tăng tốc nhanh hay chậm"
- **Repeat key terms**: thuật ngữ mới cần xuất hiện ≥ 3 lần với context khác nhau
- **Confirmation checks**: thỉnh thoảng hỏi "Bạn nắm phần này chưa? Cần tôi nhắc lại không?"

### 3. UX cho Multi-turn Voice Dialog
- **Latency tối đa 2s** giữa user nói xong và assistant reply (CHI 2024 study cho blind users)
- **Interrupt-friendly**: user có thể "Stop, lặp lại đi" giữa lúc assistant đang đọc
- **Session memory**: nhớ context xuyên suốt session, không reset mỗi message

## So với hiện trạng (cần cải thiện)

| Tool | Strength | Limitation |
|------|----------|------------|
| Seeing AI | Free, mobile, offline-OK | Only "describe", no teach |
| Be My AI (BeMyEyes) | GPT-4V powerful | Cloud, no Vietnamese, no STEM tutor |
| VisionPal (Cornell 2026) | Latest research | Hallucination cao |
| AURA | Assistive | Generic, không edu-specific |
| Khanmigo (Khan Academy) | Tutor pedagogy tốt | Không cho khiếm thị |
| **VisionarySTEM tutor (Sprint 8.1)** | VN-first + STEM + accessibility | Cần build |

## Implementation cho Sprint 8.1

### System prompt template
```
Bạn là gia sư STEM tiếng Việt cho sinh viên khiếm thị.
Đã phân tích tài liệu: {document_summary}.
Có {n} blocks: {block_summaries}.

Quy tắc trả lời:
1. Tiếng Việt tự nhiên, KHÔNG đọc công thức kiểu tiếng Anh
2. Câu ngắn (≤ 25 từ/câu), phù hợp đọc TTS
3. Có ví dụ cụ thể đời sống VN khi giải thích
4. Cite block (vd: "trong block_002 có công thức...")
5. Cuối câu trả lời, suggest 1-2 follow-up câu hỏi
```

### Conversation state
```python
class ChatSession:
    tenant_id: str
    document_id: str
    session_id: str  # uuid
    messages: list[Message]  # role={user, assistant, system}, content, timestamp, cited_blocks?
    created_at: datetime
    last_active_at: datetime
```

### Suggested follow-ups (auto-generate)
Sau mỗi reply, Gemini trả thêm `suggested_followups: list[str]`:
- "Giải thích bằng cách khác?"
- "Cho tôi 1 ví dụ thực tế"
- "Tôi muốn nghe lại block X"
- "Tóm tắt toàn bộ trang"

## Papers cần đọc
- [arXiv 2504.17117](https://arxiv.org/html/2504.17117v1) — AI for Accessible Education: Personalized Audio-Based Learning for Blind Students
- "VisionPal: Conversational Agent for Visual Accessibility" (Cornell 2026)
- ASSETS 2024-2026 proceedings (acm.org/conference/assets)
- CHI 2026 — Accessibility track
- Khan Academy — Khanmigo case study
- Microsoft Inclusive Design Toolkit (microsoft.com/design/inclusive)

## Sources & Reading Order
1. arXiv 2504.17117 (foundational, đọc trước)
2. ACM XRDS 2025 multimodal chart accessibility (Sprint 8.3 reference)
3. ASSETS 2025 keyword "tutor" "STEM"
4. VnBEyes / Sở GD-ĐT TP.HCM EDUi blogs (research findings/14)
