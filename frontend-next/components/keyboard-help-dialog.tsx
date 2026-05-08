"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Keyboard, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKeyboardShortcuts, formatShortcut, type Shortcut } from "@/lib/use-keyboard-shortcuts";

const GLOBAL_SHORTCUTS: Omit<Shortcut, "action">[] = [
  { key: "?", description: "Hiện bảng phím tắt" },
  { key: "g h", description: "Về trang chủ (gõ 'g' rồi 'h')" },
  { key: "g w", description: "Mở Workspace (g + w)" },
  { key: "g t", description: "Mở Gia sư (g + t)" },
  { key: "g l", description: "Mở Camera Live (g + l)" },
  { key: "g p", description: "Mở Pricing (g + p)" },
  { key: " ", description: "Phát / tạm dừng audio đang focus", skipInInputs: true },
  { key: "ArrowDown", description: "Block tiếp theo (trong workspace)" },
  { key: "ArrowUp", description: "Block trước đó" },
  { key: "Escape", description: "Đóng dialog / huỷ thao tác" },
  { key: "/", description: "Focus ô tìm kiếm / câu hỏi", skipInInputs: true },
];

/**
 * Global keyboard help dialog. Shown when user presses '?'.
 * Also provides routing shortcuts (g h, g w, ...).
 */
export function KeyboardHelpDialog() {
  const [open, setOpen] = useState(false);
  const [gPressed, setGPressed] = useState(false);

  // 'g' prefix routing — gives "vim-like" experience
  useEffect(() => {
    if (!gPressed) return;
    const t = setTimeout(() => setGPressed(false), 1500);
    return () => clearTimeout(t);
  }, [gPressed]);

  useKeyboardShortcuts(
    [
      { key: "?", description: "Help", action: () => setOpen(true), preventDefault: true, skipInInputs: true },
      {
        key: "g",
        description: "g-prefix",
        action: () => setGPressed(true),
        skipInInputs: true,
      },
      ...(gPressed
        ? [
            { key: "h", description: "home", action: () => { window.location.href = "/"; setGPressed(false); }, skipInInputs: true },
            { key: "w", description: "workspace", action: () => { window.location.href = "/workspace"; setGPressed(false); }, skipInInputs: true },
            { key: "t", description: "tutor", action: () => { window.location.href = "/tutor"; setGPressed(false); }, skipInInputs: true },
            { key: "l", description: "live", action: () => { window.location.href = "/live"; setGPressed(false); }, skipInInputs: true },
            { key: "p", description: "pricing", action: () => { window.location.href = "/pricing"; setGPressed(false); }, skipInInputs: true },
          ]
        : []),
    ],
    true,
  );

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Mở bảng phím tắt (?)"
          className="h-9 w-9"
          title="Phím tắt (?)"
        >
          <Keyboard className="size-4" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-card p-6 shadow-lg rounded-2xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95">
          <div className="flex items-start justify-between">
            <div>
              <Dialog.Title className="text-xl font-bold">Phím tắt bàn phím</Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground mt-1">
                Voice-first UX cho người khiếm thị — di chuyển nhanh không cần chuột.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Đóng">
                <X className="size-4" />
              </Button>
            </Dialog.Close>
          </div>
          <div className="space-y-1.5 max-h-[60vh] overflow-y-auto pr-2">
            {GLOBAL_SHORTCUTS.map((sc) => (
              <div
                key={sc.key + sc.description}
                className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 hover:bg-muted/40"
              >
                <span className="text-sm">{sc.description}</span>
                <kbd className="inline-flex items-center rounded-md border bg-muted px-2 py-0.5 text-xs font-mono">
                  {formatShortcut({ key: sc.key })}
                </kbd>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground border-t pt-3">
            💡 Phím tắt hoạt động ở mọi trang. Nhấn <kbd className="rounded border bg-muted px-1">?</kbd> bất cứ lúc nào để mở lại bảng này.
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
