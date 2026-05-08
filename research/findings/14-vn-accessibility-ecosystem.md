# Hệ sinh thái Accessibility tại Việt Nam

## TL;DR
- Thị trường khiếm thị VN: **~1 triệu người** (theo Hội Người Mù VN), trong đó ~60,000 trong độ tuổi học sinh/sinh viên.
- Tools VN hiện có: **Gemini Live + Dot Pad** (đắt), **VnBEyes**, dự án sinh viên — hầu như chưa có tool chuyên cho **giáo dục STEM**.
- **Trường Phổ thông Đặc biệt Nguyễn Đình Chiểu** (TP.HCM, Hà Nội) là partner pilot lý tưởng.
- **Sở GD-ĐT TP.HCM EDUi** + **Sở KH&CN TP.HCM** có grant + ecosystem hỗ trợ.

## Stakeholder map

### Trường học target (tiếp cận pilot)
| Trường | Địa điểm | Số HS khiếm thị | Đã dùng tech |
|--------|----------|----------------|--------------|
| **Trường PT Đặc biệt Nguyễn Đình Chiểu** | TP.HCM, Hà Nội | ~300 mỗi cơ sở | Dot Pad pilot 2024-2025 |
| **Trường PT Đặc biệt Bilingual** | TP.HCM | ~50 | Cơ bản |
| **Trường THPT năng khiếu/THCS hoà nhập** | Mọi tỉnh | Phân tán | Screen reader VN |
| **Đại học có sinh viên khiếm thị** (TDTU, ĐHQG, HUS, Sư phạm) | Toàn quốc | ~2000+ | Tự xoay xở |

### Tổ chức/đơn vị partner
- **Hội Người Mù Việt Nam (VBU)** — vbu.org.vn — toàn quốc, cấp giấy chứng nhận, cộng đồng lớn
- **Sở GD-ĐT TP.HCM** — chương trình EDUi 2025 (nền tảng giáo dục mở), có thể tích hợp
- **Sở KH&CN TP.HCM** — có grant cho dự án "AI tiếp cận thông tin" 2025
- **Bộ Giáo dục & Đào tạo** — Vụ Giáo dục Trung học, Vụ Giáo dục Đặc biệt
- **Microsoft AI for Good Vietnam** — grant CSR
- **Google.org / Google for Education** — partner tech
- **Hội đồng đổi mới sáng tạo TP.HCM (Saigon Innovation Hub)** — incubator

### Đối thủ / Tool VN hiện có
| Tool | Loại | Mạnh | Yếu |
|------|------|------|-----|
| **Dot Pad VN pilot** | Hardware tactile | Chính xác | Đắt ~30-50tr/chiếc |
| **Gemini Live (Google)** | Multimodal voice | Free | Không edu-specific, không VN-context |
| **VnBEyes** | App đọc môi trường | VN UI | Generic, không STEM |
| **NVDA + đọc tiếng Việt** | Screen reader | Open source | Không hiểu math |
| **JAWS Vietnamese voice** | Premium screen reader | Mature | Đắt, không multimodal |

→ **VisionarySTEM là tool đầu tiên** chuyên cho STEM accessibility VN. Lợi thế cạnh tranh rõ rệt.

## Đặc điểm UX cần lưu ý cho VN

### Ngôn ngữ
- **Tiếng Việt phải có dấu**: TTS phải đọc đúng "Niu-tơn" chứ không "Newton" (hoặc đọc cả 2 lần khi gặp tên riêng)
- **Tiếng Anh xen kẽ**: SGK mới có nhiều thuật ngữ Anh (calculus, derivative). Cần code-switching natural
- **Toán dạng VN**: "phương trình bậc hai" thay "quadratic equation"; "đạo hàm" thay "derivative"; ký hiệu $f'(x)$ đọc "f phẩy của x"

### Văn hoá học tập
- **Tôn trọng giáo viên**: chatbot xưng "tôi" với user là "bạn"; KHÔNG xưng "thầy/cô"
- **Tránh gọi user là "em"**: khiếm thị ở đại học không phải trẻ em
- **Đoàn thể**: mention "lớp", "nhóm học" hợp với văn hoá VN

### Kỹ thuật
- **Mạng yếu**: 30-40% sinh viên VN dùng 4G hạn chế. Streaming SSE với fallback batch là cần thiết
- **Smartphone phổ biến** > tablet/laptop. Mobile-responsive là MUST
- **Lưu trữ địa phương**: cache TTS aggressive vì người dùng có thể nghe lại offline

## Pricing model phù hợp VN

| Tier | Giá | Đối tượng | Ghi chú |
|------|-----|-----------|---------|
| **Free** | 0đ | Sinh viên cá nhân | 5 PDF/tháng, basic TTS |
| **Student Pro** | 49,000 đ/tháng | SV trả phí | 50 PDF/tháng, premium TTS, tutor unlimited |
| **University License** | 5-50tr/năm | TDTU, ĐHQG, HUS | Multi-user (50-500 seat), admin dashboard |
| **NGO Grant** | 0đ | Hội Người Mù, Trường NĐC | Sponsor bởi Microsoft AI for Good / Sở KHCN |
| **Enterprise** | Custom | Quốc tế (RNIB, ACB) | White-label, EPUB3 export, SLA |

## Path-to-market (12 tháng)

### Tháng 1-2 (đang làm)
- ✅ MVP demo cho TDTU Vibe Coding 2026
- 🔜 Pilot với 5-10 sinh viên TDTU khiếm thị

### Tháng 3-5
- Mở rộng pilot Trường NĐC TP.HCM (với phối hợp Sở GD)
- Apply Microsoft AI for Good grant
- Tham dự Saigon Innovation Hub demoday

### Tháng 6-8
- Beta launch B2C — Student Pro tier qua app store
- Sign first university B2B (TDTU hoặc HUS)
- Submit paper ASSETS 2026 (deadline ~tháng 5)

### Tháng 9-12
- Thoả thuận với Sở GD TP.HCM tích hợp EDUi
- Apply Google.org grant
- Expand sang trường khác

## Sources
- Hội Người Mù VN: https://vbu.org.vn
- Sở KH&CN TP.HCM: https://dost.hochiminhcity.gov.vn
- Trường NĐC TP.HCM: ndc-hcm.edu.vn
- EDUi platform: announcement Sở GD 2025
- Microsoft AI for Good: microsoft.com/ai-for-good
- Saigon Innovation Hub: saigonhub.org

## Action items immediate
1. **Soạn Pitch deck VN** — dùng [docs/SLIDE_OUTLINE.md](../../docs/SLIDE_OUTLINE.md) làm base, dịch sang vibe đầu tư
2. **Liên hệ Trường NĐC** — gửi demo video + offer free pilot
3. **Apply Microsoft AI for Good** — deadline rolling
4. **Đăng ký bản quyền + thương hiệu** "VisionarySTEM" tại Cục Sở hữu Trí tuệ VN
