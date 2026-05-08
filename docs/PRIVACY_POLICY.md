# Chính sách Bảo mật — VisionarySTEM
# Privacy Policy

**Phiên bản:** 1.0  
**Hiệu lực từ:** 2026-04-28  
**Liên hệ:** privacy@visionarystem.com

---

## Tóm tắt 30 giây

- ✅ Tài liệu của bạn chỉ dùng để **phân tích cho bạn**, không train AI khác.
- ✅ Lưu trữ tối đa 90 ngày, sau đó tự xoá.
- ✅ Free user lưu 7 ngày, Pro 30 ngày, Enterprise tuỳ chỉnh.
- ✅ Không bán dữ liệu cá nhân cho bên thứ 3.
- ⚠️ Gemini API (Google) sẽ thấy nội dung khi phân tích — chính sách Google áp dụng song song.

---

## 1. Dữ liệu chúng tôi thu thập

### A. Dữ liệu bạn cung cấp
- Email, mật khẩu (hash bcrypt) khi đăng ký.
- Tài liệu PDF/ảnh khi upload.
- Câu hỏi text/voice khi dùng tutor/spatial query.
- Preferences (theme, TTS rate/pitch).

### B. Dữ liệu tự động
- Logs: timestamp, endpoint, IP (anonymized sau 30 ngày), user-agent.
- Usage metrics: số PDF/tháng, audio min, token Gemini.
- Cookies: session JWT (httpOnly), theme localStorage.

### C. Không thu thập
- ❌ Browsing history ngoài VisionarySTEM.
- ❌ Microphone audio ngoài voice query.
- ❌ Webcam frames ngoài Camera Live mode (chỉ khi user kích hoạt).

## 2. Cách chúng tôi dùng dữ liệu

| Mục đích | Dữ liệu | Cơ sở pháp lý |
|----------|---------|---------------|
| Phân tích tài liệu | Nội dung upload | Hợp đồng dịch vụ |
| Cá nhân hoá tutor | Conversation history | Hợp đồng dịch vụ |
| Billing | Email, plan, payment ID | Hợp đồng dịch vụ |
| Cải thiện sản phẩm | Anonymized usage logs | Lợi ích chính đáng |
| Email thông báo | Email | Consent (opt-in) |
| Compliance pháp lý | Tất cả | Nghĩa vụ pháp lý |

**KHÔNG dùng để:**
- Train mô hình AI của VisionarySTEM hoặc bên thứ 3.
- Bán cho ad network, broker dữ liệu.

## 3. Bên thứ 3

### Bắt buộc (vận hành dịch vụ)
- **Google Gemini API**: gửi tài liệu cho phân tích AI. Áp dụng [Google AI Privacy](https://ai.google/responsibility/privacy/). Theo Google policy, prompts/responses không dùng để train Gemini cho enterprise/paid tier.
- **Microsoft Edge TTS**: text → speech. Không lưu trữ.
- **Cloudflare R2 / MinIO**: lưu file upload tạm. Encrypt at rest.
- **PostgreSQL (Supabase/Neon)**: metadata + user.

### Optional (Pro+)
- **Mathpix**: chỉ kích hoạt khi user opt-in (Pro tier, công thức siêu phức tạp).
- **PhoWhisper (VinAI)**: voice query. On-prem option cho Enterprise.
- **Paddle / PayOS**: thanh toán. Chỉ chia sẻ email + plan, không nội dung.

## 4. Lưu trữ & xoá dữ liệu

| Loại dữ liệu | Free | Pro | University | Enterprise |
|--------------|------|-----|------------|------------|
| Tài liệu upload | 7 ngày | 30 ngày | 90 ngày | Tuỳ chỉnh |
| Conversation history | 1 ngày | 30 ngày | 90 ngày | Tuỳ chỉnh |
| Audio TTS cache | 7 ngày | 30 ngày | 30 ngày | Tuỳ chỉnh |
| Usage logs (raw) | 30 ngày | 30 ngày | 30 ngày | 30 ngày |
| Usage logs (anonymized aggregate) | Mãi mãi | Mãi mãi | Mãi mãi | Mãi mãi |
| Account info (email, billing) | Cho đến khi xoá tài khoản | | | |

**Xoá tài khoản**: Settings → "Xoá tài khoản". Mọi dữ liệu xoá trong 30 ngày (trừ logs anonymized & nghĩa vụ pháp lý như invoice).

## 5. Bảo mật

- HTTPS bắt buộc trên mọi endpoint.
- JWT session token, httpOnly + Secure cookies.
- Mật khẩu hash bcrypt (12 round).
- Database encrypt at rest (AES-256).
- File upload virus-scan (ClamAV).
- Annual security audit (planned).
- Secrets trong AWS/GCP Secrets Manager, không hardcode.

## 6. Quyền của bạn (GDPR + Việt Nam Luật BVDLCN 2025)

Bạn có quyền:
- **Truy cập**: tải toàn bộ data của mình (Settings → Export Data).
- **Sửa**: cập nhật email, name, prefs.
- **Xoá**: xoá tài khoản & data.
- **Hạn chế xử lý**: yêu cầu pause AI processing.
- **Phản đối marketing**: opt-out email một click.
- **Khiếu nại**: gửi privacy@visionarystem.com hoặc Cục An toàn Thông tin (Bộ TTTT).

Phản hồi yêu cầu trong **30 ngày**.

## 7. Trẻ em

Dịch vụ không hướng tới trẻ <13 tuổi (COPPA). Người dùng 13-18 tuổi cần phụ huynh đồng ý. Trường học pilot cho học sinh khiếm thị cần ký DPA (Data Processing Agreement) riêng.

## 8. Thay đổi chính sách

Khi thay đổi material → email báo trước 30 ngày + banner trong app. Bản cũ lưu tại `docs/privacy-history/`.

## 9. Liên hệ

- Privacy: privacy@visionarystem.com
- Data Protection Officer (DPO): dpo@visionarystem.com (Enterprise EU only)
- Khiếu nại: Cục An toàn Thông tin, Bộ TT&TT

---

*Cuối cùng: chúng tôi build dự án này CHO người khiếm thị Việt Nam. Quyền riêng tư của bạn không phải sản phẩm.*
