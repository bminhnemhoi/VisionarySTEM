# Vietnam Payment Gateway cho VisionarySTEM SaaS

## TL;DR
- **Stripe KHÔNG hoạt động official ở VN** — cần inc UK/SG.
- **VNPay** xử lý 40% giao dịch số VN, có connector với 50+ ngân hàng → **PHẢI tích hợp** cho B2B/B2C VN.
- **MoMo** 31 triệu user (~1/3 dân số) → **PHẢI tích hợp** cho B2C.
- **ZaloPay** mạnh trong nhóm GenZ.
- **Visa/Mastercard direct** qua Stripe (nếu inc nước ngoài) cho B2B Quốc tế.

## Chiến lược billing đề xuất

### Tier free (B2C)
- Edge TTS, Gemini Flash, 5 PDF/tháng
- Không cần payment

### Tier Student Pro (B2C – 99k VNĐ/tháng)
- 50 PDF/tháng, premium TTS (VieNeu)
- Payment: MoMo / ZaloPay / VNPay QR
- **Dùng [Casso.vn](https://casso.vn)** hoặc **PayOS** — aggregator hợp pháp

### Tier University (B2B – $200-2000/tháng theo seat)
- Multi-user, admin dashboard, on-premise option
- Payment: VNPay business invoice + chuyển khoản (yêu cầu fapiao)
- **Hợp đồng giấy** — cần bộ phận sales

### Tier Enterprise / NGO (B2B QT – $1k-10k/tháng)
- White-label, SLA 99.9%, dedicated support
- Payment: Stripe (qua entity SG/UK), wire transfer USD
- Audit log accessibility theo WCAG, EPUB3 export

## Kỹ thuật tích hợp
| Provider | SDK Python | Webhook | Subscription support |
|----------|-----------|---------|-----------------------|
| VNPay | Có (mới) | Có | ❌ — phải tự build |
| MoMo Business | REST API | Có | ❌ |
| ZaloPay | REST API | Có | ❌ |
| PayOS | Có | Có | ✅ partial |
| Casso | REST | Có | – aggregator |
| Stripe (offshore) | Tốt | Tốt | ✅ |
| Paddle (Merchant of Record) | Tốt | Tốt | ✅ — handle VAT toàn cầu |

**Khuyến nghị**: Bắt đầu **Paddle** (Merchant of Record) cho Pro tier (tự handle thuế, hoá đơn EU/US) + **PayOS** cho VN local. Khi scale → tự build VNPay direct.

## Điểm rủi ro
- VN luật thuế: cần đăng ký ngành nghề, hoá đơn điện tử (e-invoice)
- B2B VN thường yêu cầu hợp đồng giấy + chuyển khoản — **không** phải online subscription
- Refund: VN không có quy định subscription rõ ràng — phải có policy minh bạch

## Sources
- [Stripe Vietnam guide](https://stripe.com/resources/more/payments-in-vietnam)
- [Best Payment Gateways VN 2026](https://nowpayments.io/blog/payment-gateway-vietnam)
- [Mad Devs Vietnam Gateways](https://maddevs.io/blog/leading-payment-gateways-in-vietnam-to-start-your-business/)
- [Visa partners MoMo VNPAY ZaloPay](https://fintech.global/2024/05/27/visa-partners-with-momo-vnpay-and-zalopay-to-enhance-digital-payments-in-vietnam/)
- [Vietnam Mobile Payments Market](https://www.mordorintelligence.com/industry-reports/vietnam-mobile-payments-market)
