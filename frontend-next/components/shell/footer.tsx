import Link from "next/link";
import { Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t bg-card/50 py-8 mt-12" role="contentinfo">
      <div className="container flex flex-col items-center justify-between gap-4 md:flex-row">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>VisionarySTEM v2.1</span>
          <span aria-hidden>•</span>
          <span>TDTU Vibe Coding 2026</span>
          <span aria-hidden>•</span>
          <span className="flex items-center gap-1">
            Made with <Heart className="size-3.5 fill-red-500 text-red-500" aria-label="love" /> for accessibility
          </span>
        </div>
        <div className="flex items-center gap-5 text-sm">
          <Link href="/settings" className="text-muted-foreground hover:text-foreground transition-colors">
            Cài đặt
          </Link>
          <Link href="https://github.com" className="text-muted-foreground hover:text-foreground transition-colors">
            GitHub
          </Link>
          <Link href="/about" className="text-muted-foreground hover:text-foreground transition-colors">
            Giới thiệu
          </Link>
        </div>
      </div>
    </footer>
  );
}
