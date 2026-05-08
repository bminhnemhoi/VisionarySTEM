"use client";

import { useEffect, useRef } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Link2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface UrlInputDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called with the entered URL when user confirms (Enter or Submit). */
  onSubmit: (url: string) => void;
  /** Called when user cancels (Esc or Cancel button). */
  onCancel?: () => void;
}

/**
 * Accessible URL input — for voice-driven "tải link" flow.
 *
 * Auto-focus input on open so user can:
 * - Paste URL via Ctrl+V
 * - Type URL with keyboard
 * - Read URL aloud (if Web Speech captures it as transcript)
 *
 * Enter to submit, Esc to cancel — both spoken aloud by parent.
 */
export function UrlInputDialog({ open, onOpenChange, onSubmit, onCancel }: UrlInputDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      // Small delay to wait for Dialog mount
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const url = inputRef.current?.value.trim();
    if (url) onSubmit(url);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-card p-6 shadow-lg rounded-2xl"
          onEscapeKeyDown={() => onCancel?.()}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                <Link2 className="size-5" aria-hidden />
              </div>
              <div>
                <Dialog.Title className="text-xl font-bold">Dán link tài liệu</Dialog.Title>
                <Dialog.Description className="text-sm text-muted-foreground mt-1">
                  Hỗ trợ PDF, ảnh, hoặc bài viết web học liệu (Wikipedia, vietjack, hocmai, v.v.)
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Đóng" onClick={() => onCancel?.()}>
                <X className="size-4" />
              </Button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <label htmlFor="vs-url-input" className="block text-sm font-medium">
              Link (bấm Control V để dán, hoặc gõ)
            </label>
            <input
              ref={inputRef}
              id="vs-url-input"
              type="url"
              placeholder="https://example.com/file.pdf"
              required
              className="w-full rounded-xl border bg-background px-4 py-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-describedby="vs-url-hint"
            />
            <p id="vs-url-hint" className="text-xs text-muted-foreground">
              Bấm Enter để xác nhận, hoặc Esc để huỷ. Tối đa 20 megabyte.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => onCancel?.()}>
                Huỷ (Esc)
              </Button>
              <Button type="submit" variant="gradient">
                Phân tích link
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
