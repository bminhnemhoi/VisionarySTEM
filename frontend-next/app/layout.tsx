import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";

import { ThemeProvider } from "@/components/theme-provider";
import { Topbar } from "@/components/shell/topbar";
import { Footer } from "@/components/shell/footer";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GlobalAudioControls } from "@/components/global-audio-controls";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin", "vietnamese"],
  variable: "--font-jakarta",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "VisionarySTEM — Trợ lý AI cho sinh viên khiếm thị",
    template: "%s · VisionarySTEM",
  },
  description:
    "Phân tích tài liệu STEM tiếng Việt thành giọng đọc tự nhiên, truy vấn theo không gian, và gia sư AI cá nhân hoá cho sinh viên khiếm thị.",
  keywords: ["accessibility", "blind", "STEM", "Vietnamese", "AI tutor", "education"],
  authors: [{ name: "VisionarySTEM Team" }],
  openGraph: {
    type: "website",
    locale: "vi_VN",
    title: "VisionarySTEM — Trợ lý AI cho sinh viên khiếm thị",
    description: "Tài liệu STEM tiếng Việt → giọng đọc tự nhiên + gia sư AI.",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAFAFA" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning className={`${jakarta.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="friendly-light"
          themes={["friendly-light", "friendly-dark", "high-contrast"]}
          enableSystem={false}
          disableTransitionOnChange
        >
          <TooltipProvider delayDuration={300}>
            <a href="#main-content" className="skip-link">
              Bỏ qua tới nội dung chính
            </a>
            <div className="flex min-h-screen flex-col">
              <Topbar />
              <main id="main-content" className="flex-1" role="main">
                {children}
              </main>
              <Footer />
            </div>
            <GlobalAudioControls />
            <Toaster richColors position="top-right" closeButton />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
