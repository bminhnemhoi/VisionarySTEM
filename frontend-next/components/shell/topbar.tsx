"use client";

import Link from "next/link";
import { Microscope } from "lucide-react";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { KeyboardHelpDialog } from "@/components/keyboard-help-dialog";

/**
 * Minimal topbar — voice mode is the only mode.
 * No nav clutter, just brand + theme + keyboard help.
 */
export function Topbar() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Link
          href="/"
          className="flex items-center gap-2.5 transition-transform hover:scale-[1.02]"
          aria-label="VisionarySTEM trang chủ"
        >
          <div className="flex size-9 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-md">
            <Microscope className="size-5" aria-hidden />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-bold leading-none text-gradient">VisionarySTEM</span>
            <span className="text-[11px] leading-none text-muted-foreground">
              Trợ lý voice cho khiếm thị
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <KeyboardHelpDialog />
          <ThemeSwitcher />
        </div>
      </div>
    </header>
  );
}
