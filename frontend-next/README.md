# VisionarySTEM Next.js Frontend

> Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui-style primitives.
> Friendly Education theme inspired by Duolingo / Khan Academy.
> 3 themes: Friendly Light, Friendly Dark, High Contrast (WCAG AAA).

## Tech stack
- Next.js 14 (App Router, Server Components + Client Components)
- TypeScript strict
- TailwindCSS 3 + tailwindcss-animate
- Radix UI primitives (button, card, tabs, tooltip, scroll-area, progress, sonner toast)
- Framer Motion (subtle animations)
- next-themes (3-mode switcher)
- Lucide icons
- API proxy via `/api/proxy/[...path]` (hides backend URL, avoids CORS)

## Cài đặt

```bash
cd frontend-next

# Yêu cầu Node >= 18.17 (Next 14)
npm install
# hoặc nếu có pnpm:
# pnpm install
```

## Chạy dev

Terminal 1 — backend (FastAPI):
```bash
cd d:/VisionarySTEM
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend Next.js:
```bash
cd d:/VisionarySTEM/frontend-next
npm run dev
# Mở http://localhost:3000
```

Backend URL configurable qua `BACKEND_URL` env (mặc định `http://127.0.0.1:8000`):
```bash
BACKEND_URL=http://localhost:8000 npm run dev
```

## Pages

| Path | Mô tả |
|------|-------|
| `/` | Marketing home (hero + features + stats + CTA) |
| `/workspace` | Phân tích PDF/ảnh — streaming SSE + spatial query + audio |
| `/tutor` | Gia sư AI — multi-turn chat về tài liệu |
| `/live` | Camera Live — mô tả slide/bảng realtime |

## Theme switcher

Header có icon (☀️/🌙/👁) ở trên cùng, persist trong localStorage.

- **friendly-light** (default): pastel xanh tím, rounded-2xl, illustrations
- **friendly-dark**: same vibes nhưng dark
- **high-contrast**: đen + vàng + cyan focus ring (WCAG AAA cho khiếm thị)

## Component organization

```
components/
├── ui/             # Radix-based primitives (button, card, tabs, ...)
├── analyze/        # Upload + block card + (future) PDF overlay
├── tutor/          # Chat panel cho /tutor page
├── audio/          # Custom AudioPlayer
├── camera/         # Live capture với getUserMedia
├── shell/          # Topbar, footer
└── theme-switcher.tsx
```

## Build production

```bash
npm run build
npm start
```

Lighthouse target: Accessibility ≥ 95, Performance ≥ 85.

## Troubleshooting

- **`Cannot find module '@radix-ui/...'`**: Chưa `npm install`. Chạy `npm install` trong folder `frontend-next/`.
- **Backend unreachable (502)**: Đảm bảo backend chạy ở `127.0.0.1:8000`.
- **Camera không bật**: Browser cần HTTPS hoặc `localhost` để cấp `getUserMedia` quyền. Trên IP khác cần config HTTPS.
- **Theme không đổi**: Kiểm tra `data-theme` attribute trên `<html>` element và localStorage `theme` key.
