# Tuyên bố Accessibility — VisionarySTEM
# Accessibility Statement

**Phiên bản:** 1.0  
**Hiệu lực từ:** 2026-04-28  
**Cập nhật gần nhất:** 2026-04-28

---

## Cam kết của chúng tôi

VisionarySTEM được xây dựng **CHO** sinh viên khiếm thị Việt Nam. Accessibility không phải tính năng phụ — đó là **lý do dự án tồn tại**.

Chúng tôi cam kết tuân thủ:
- **WCAG 2.2 Level AA** (mọi trang) — tối thiểu
- **WCAG 2.2 Level AAA** trong chế độ "High Contrast" — cho người thị lực rất thấp
- **EN 301 549** (chuẩn EU public sector) — cho khách Enterprise quốc tế
- **EPUB 3.3 + a11y meta** — cho file export
- **NIMAS** — chuẩn textbook Mỹ K-12

## Thực trạng tuân thủ (2026-04-28)

### ✅ Đã tuân thủ
- **Color contrast**: ≥ 7:1 (AAA) ở chế độ High Contrast; ≥ 4.5:1 (AA) ở Friendly themes
- **Font size**: 18px+ ở High Contrast; 16px+ ở Friendly (resize tới 200% không vỡ layout)
- **Click target**: ≥ 44×44px (AAA)
- **Keyboard navigation**: 100% chức năng truy cập bằng phím (Tab, Enter, Space, ↑↓, Esc, ?, g+letter)
- **Focus indicators**: ring 2px+ rõ rệt, ring 4px ở High Contrast (đáp ứng WCAG 2.4.7)
- **Skip links**: "Bỏ qua tới nội dung chính" ở đầu mỗi trang
- **ARIA roles**: button, dialog, navigation, main, region, math, figure, contentinfo
- **Screen reader tested**: NVDA (Windows), JAWS (sample), VoiceOver iOS — pass cơ bản
- **Theme switcher**: 3 modes (Friendly Light/Dark + High Contrast)
- **TTS Vietnamese tự nhiên**: spoken_text 100% tiếng Việt, không "F equals m a"
- **TTS rate/pitch tuỳ chỉnh**: -50% đến +100% (người khiếm thị thường thích +50-100%)
- **Sonification**: biểu đồ → audio cho chart accessibility
- **EPUB3 export với MathML**: tương thích Thorium Reader, iBooks

### 🟡 Đang cải thiện (Q2-Q3/2026)
- **Tích hợp Dot Pad / refreshable Braille display**: roadmap Sprint 6+
- **Sign language (VSL) interpreter video**: cho người vừa khiếm thị + khiếm thính
- **Audio descriptions** cho video demo
- **Cognitive accessibility**: simplified language toggle (cho khuyết tật học tập)
- **Touch target spacing trên mobile**: kiểm tra kỹ hơn

### 🔴 Hạn chế đã biết
- **Camera Live cần webcam + cấp quyền browser** — không hoạt động trên một số trình duyệt cũ
- **PDF có công thức quá phức tạp** (matrix, integral nhiều biến) đôi khi sai LaTeX → cần Critique loop (Pro tier)
- **Navigation bằng giọng nói chưa hỗ trợ tiếng Việt natively** — STT đang dùng PhoWhisper (cần GPU server side cho Pro)
- **Unicode Braille là hiển thị mô phỏng**, chưa kết nối hardware Braille printer

## Cách báo lỗi accessibility

Bạn gặp vấn đề khi dùng VisionarySTEM với screen reader, bàn phím, hoặc thiết bị hỗ trợ?

**Liên hệ ưu tiên:**
- Email: a11y@visionarystem.com (phản hồi trong 24h cho lỗi nghiêm trọng)
- GitHub Issue: github.com/[team]/VisionarySTEM/issues (gắn label `accessibility`)
- Hotline khẩn (Enterprise): [Để trống]

**Khi báo cáo, vui lòng cung cấp:**
1. Trang đang dùng (URL hoặc tên section)
2. Trình duyệt + screen reader (vd: Chrome 120 + NVDA 2024.1)
3. Thao tác đang làm (vd: "đang nhấn Tab tới nút Phân tích nhưng focus không hiện")
4. Mong muốn hành vi gì (vd: "expected focus ring rõ + screen reader đọc nhãn")

**Cam kết SLA fix lỗi a11y:**
- Critical (block hoàn toàn): 48 giờ
- Major (vỡ flow chính): 7 ngày
- Minor (cosmetic): 30 ngày

## Đánh giá độc lập

Dự định 2026-Q3:
- Audit bởi **W3C Accessibility Conformance Testing (ACT)**
- Audit bởi **Hội Người Mù Việt Nam (VBU)** — review bởi user thật
- **axe DevTools** + **WAVE** automated scan trong CI

Báo cáo audit công khai tại `docs/audits/`.

## Tham chiếu

- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- EN 301 549: https://www.etsi.org/deliver/etsi_en/301500_301599/301549/
- Vietnam Luật Người Khuyết tật 2010 + sửa đổi 2024
- ADA (Americans with Disabilities Act) Title III digital
- DAISY Consortium standards: https://daisy.org/

## Phản hồi từ cộng đồng

> "Lần đầu tôi đọc được file PDF công thức vật lý mà không cần nhờ bạn đọc giúp. Thay đổi cuộc đời." — *Sinh viên TDTU, beta tester*

> "Theme High Contrast của VisionarySTEM là duy nhất trên thị trường VN tuân WCAG AAA cho dạng SaaS." — *Hội Người Mù VN*

(Quotes là minh hoạ — sẽ thay bằng real testimonial sau pilot)

---

*"Accessibility không phải tính năng — đó là quyền cơ bản. Chúng tôi build dự án này vì chúng tôi tin điều đó."*

— VisionarySTEM Team
