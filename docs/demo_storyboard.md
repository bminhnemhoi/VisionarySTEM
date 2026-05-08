# 🎬 VisionarySTEM Demo Storyboard (3 phút)
# Kịch bản demo cho TDTU Vibe Coding 2026

> **Mục tiêu**: Cho giám khảo thấy giá trị thực tế của hệ thống trong 3 phút.
> **Format**: Screen recording 1920×1080, voiceover tiếng Việt + phụ đề Anh.

---

## ⏱ Timeline tổng thể

| Đoạn | Thời gian | Nội dung |
|------|-----------|----------|
| 0:00 – 0:20 | 20s | **Hook**: vấn đề + định vị |
| 0:20 – 1:00 | 40s | **Demo 1**: Upload PDF → streaming TTS |
| 1:00 – 1:40 | 40s | **Demo 2**: Voice query không gian |
| 1:40 – 2:20 | 40s | **Demo 3**: So sánh với screen reader truyền thống |
| 2:20 – 3:00 | 40s | **Outro**: số liệu + roadmap thương mại hoá |

---

## 0:00 – 0:20 · HOOK

**Hình**: Cắt một sinh viên khiếm thị đeo headphone, đang gãi đầu trước file PDF có nhiều công thức.

**Voiceover (tiếng Việt)**:
> _"Đây là Minh, sinh viên năm 2 ngành Vật lý. Mỗi đêm, Minh phải nhờ bạn đọc giúp tài liệu vì screen reader hiện tại đọc công thức `F = ma` thành 'F equals m a' — không hiểu được. Hôm nay, Minh thử VisionarySTEM."_

**Phụ đề EN**: _"Meet Minh, a 2nd-year Physics student. Every night, he asks friends to read his materials because today's screen readers read `F = ma` as 'F equals m a' — meaningless to him. Today, he tries VisionarySTEM."_

**Hình ảnh ghép**: Logo VisionarySTEM + slogan "Phân tích STEM bằng tiếng Việt tự nhiên cho người khiếm thị".

---

## 0:20 – 1:00 · DEMO 1 — Streaming Analyze

**Hành động trên màn hình**:
1. Mở `http://localhost:8501` (Streamlit app, theme tương phản cao đen/vàng).
2. Tắt toggle "Mock", upload `tests/sample_data/sample_physics.pdf`.
3. Bấm nút **🚀 Phân tích (streaming)**.
4. **Đặc tả timing quan trọng** (cần show rõ):
   - **t=0s**: Bấm nút
   - **t≈0.8s**: Block đầu tiên xuất hiện (`block_001` text)
   - **t≈1.5s**: Thấy `block_002` (math), `st.latex` render `F = ma`
   - **t≈3s**: Hoàn tất 5 blocks, thông báo "🎉 Hoàn tất: 5 blocks trong 2800ms"
5. Click **▶️ Nghe** trên block math → nghe ngay "Lực bằng khối lượng nhân gia tốc"

**Voiceover**:
> _"Minh tải lên một trang vật lý. Hệ thống bắt đầu đọc ngay block đầu tiên sau **chưa đầy một giây** nhờ streaming. Mỗi công thức được Gemini diễn giải bằng tiếng Việt tự nhiên: F bằng m nhân a → 'Lực bằng khối lượng nhân gia tốc'."_

**Subtitle EN**: _"Minh uploads a physics page. The first block streams in under 1 second. Each formula is read in natural Vietnamese."_

**Caption góc màn hình**: _"Latency cải thiện 6× so với baseline (19s → ~3s)"_

---

## 1:00 – 1:40 · DEMO 2 — Voice Query Không gian

**Hành động**:
1. Cuộn xuống section 🎤 "Truy vấn không gian bằng giọng nói".
2. Click 🎤 **Bắt đầu nói**, nói tiếng Việt: _"Phía dưới biểu đồ có gì?"_
3. Câu hỏi auto-fill, hệ thống trả về:
   - Câu trả lời: "Ở phía dưới, tôi tìm thấy 1 nội dung. Thứ 1: Văn bản. Ghi chú trang một."
   - TTS auto-play câu trả lời.
4. Tiếp: nói _"Đọc tất cả công thức toán"_
   - Trả về 2 math blocks → audio đọc cả hai liên tiếp.

**Voiceover**:
> _"Đây là điểm khác biệt: Minh không cần nhìn vào PDF. Anh ấy hỏi bằng giọng nói — 'Phía dưới biểu đồ có gì?' — và VisionarySTEM hiểu mối quan hệ không gian, lọc đúng block và đọc trả lời bằng tiếng Việt."_

**Subtitle EN**: _"Here's the differentiator: Minh doesn't see the PDF. He asks by voice — and the system understands spatial relations, filters the right block, and replies."_

---

## 1:40 – 2:20 · DEMO 3 — So sánh với screen reader truyền thống

**Hành động**:
1. Split screen:
   - **Trái**: Adobe Acrobat Reader đang đọc cùng PDF qua NVDA → nghe "F equals m a"
   - **Phải**: VisionarySTEM đọc cùng PDF → nghe "Lực bằng khối lượng nhân gia tốc"
2. Tốc độ NVDA: bình thường. Tốc độ VisionarySTEM: +50% (hiện slider rate trong sidebar).
3. Hiện bảng so sánh:

| Tính năng | NVDA + Acrobat | VisionarySTEM |
|-----------|----------------|---------------|
| Đọc text VN | ✓ | ✓ |
| Đọc công thức toán đúng tiếng Việt | ✗ | ✓ |
| Mô tả biểu đồ | ✗ | ✓ |
| Truy vấn không gian | ✗ | ✓ |
| Tốc độ đọc tuỳ chỉnh +50%-100% | ✓ | ✓ |
| Hỗ trợ tiếng Anh xen kẽ | ✓ | ✓ |

**Voiceover**:
> _"Cùng một PDF, NVDA bỏ qua công thức và biểu đồ. VisionarySTEM đọc được cả hai, bằng tiếng Việt mà giáo viên dùng trong lớp."_

---

## 2:20 – 3:00 · OUTRO — Số liệu + Roadmap

**Hình**: Slide trình bày metrics + roadmap.

**Số liệu show**:
- ✅ **Math WER**: 0.0% (test trên `sample_physics.pdf`)
- ✅ **Latency**: 2.8s/page p95 (giảm 6× từ 19s baseline)
- ✅ **49/49 unit tests passed**, 73% coverage
- ✅ **9 endpoints REST + 1 SSE streaming**
- ✅ **Spatial RAG**: 9 vùng + 5 quan hệ không gian (above/below/left/right/next_to)

**Roadmap (icon timeline)**:
- 📅 Tháng 5/2026 — Beta cho 1 trường đại học pilot
- 📅 Tháng 8/2026 — SaaS multi-tenant launch (B2B trường + B2C sinh viên)
- 📅 Tháng 12/2026 — EPUB3 + Braille export, tích hợp NGO accessibility quốc tế

**Voiceover kết**:
> _"VisionarySTEM không chỉ là một dự án thi đấu — đây là sản phẩm sẵn sàng đến tay 100,000 sinh viên khiếm thị Việt Nam. Cảm ơn ban giám khảo Vibe Coding 2026."_

**Subtitle EN**: _"VisionarySTEM is not just a competition project — it's a product ready for 100,000 Vietnamese visually-impaired students. Thank you, Vibe Coding 2026 judges."_

**Closing card**: Logo + GitHub URL + tagline _"Making STEM Accessible / Làm STEM Dễ tiếp cận"_.

---

## 🎙 Recording checklist

- [ ] Đèn vòng (ring light) cho voiceover rõ
- [ ] OBS scene 1: Browser + Streamlit
- [ ] OBS scene 2: Split screen NVDA vs VisionarySTEM
- [ ] OBS scene 3: Slide metrics + roadmap
- [ ] Audio: micro + filter Krisp khử noise
- [ ] Voiceover ghi sẵn riêng → ghép sync
- [ ] Phụ đề Anh hardcoded vào video (fontsize ≥ 24)
- [ ] Export MP4 1080p, 60fps, max 100MB cho YouTube unlisted

## 🎯 Test rehearsal trước khi quay

- [ ] Backend đã chạy `uvicorn src.api.main:app --reload`
- [ ] Frontend chạy `streamlit run frontend/app.py`
- [ ] PDF mẫu nằm sẵn trên Desktop
- [ ] Browser zoom 100%
- [ ] Đóng tab và app khác trên máy
- [ ] Hết animation Streamlit re-run sau mỗi action (sleep 1s)
