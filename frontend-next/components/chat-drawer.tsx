"use client";

import { useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Send, X, Volume2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ttsSpeakV2Blob } from "@/lib/api";
import type { ConversationTurn } from "./voice-mode-orchestrator";

interface ChatDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  history: ConversationTurn[];
  /** Same callback as voice — typed text goes through intent dispatcher. */
  submitText: (text: string) => void;
}

/**
 * Chat drawer — fallback khi voice không khả dụng (môi trường ồn, mic hỏng).
 *
 * - Mặc định ĐÓNG (voice-first vẫn là chủ đạo)
 * - Mở bằng FAB hoặc Ctrl + /
 * - Mirror cùng `history` từ orchestrator → đồng bộ với voice
 * - Submit text → gọi `submitText` → đi qua CHÍNH intent dispatcher của voice
 *   (nói "tài liệu mẫu" qua chat = nói qua mic)
 */
export function ChatDrawer({ open, onOpenChange, history, submitText }: ChatDrawerProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-focus input on open
  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 100);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Auto-scroll to bottom on new messages or when opening
  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history.length, open]);

  // Global Ctrl+/ toggle
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "/") {
        const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea") return;
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const handleSubmit = () => {
    const text = input.trim();
    if (!text) return;
    submitText(text);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const speakMessage = async (text: string) => {
    try {
      const blob = await ttsSpeakV2Blob(text, "Aoede", "auto");
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      audio.onerror = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      console.error("[chat-drawer] speak failed", e);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l bg-background shadow-xl data-[state=open]:animate-in data-[state=open]:slide-in-from-right"
          aria-describedby="chat-drawer-desc"
        >
          {/* Header */}
          <div className="flex items-start justify-between border-b p-4">
            <div className="space-y-1">
              <Dialog.Title className="text-lg font-bold">Khung chat</Dialog.Title>
              <Dialog.Description id="chat-drawer-desc" className="text-xs text-muted-foreground">
                Thay thế voice khi mic không khả dụng. Phím Ctrl + / để mở/đóng.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Đóng khung chat">
                <X className="size-4" />
              </Button>
            </Dialog.Close>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3" role="log" aria-live="polite">
            {history.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground space-y-2">
                <p>Chưa có tin nhắn nào.</p>
                <p>Gõ "tài liệu mẫu" để bắt đầu, hoặc bất kỳ câu hỏi nào.</p>
              </div>
            ) : (
              history.map((turn, idx) => (
                <MessageBubble key={`${turn.timestamp}-${idx}`} turn={turn} onSpeak={speakMessage} />
              ))
            )}
          </div>

          {/* Input */}
          <div className="border-t p-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nhập tin nhắn... (Enter để gửi, Shift+Enter xuống dòng)"
                rows={2}
                className="flex-1 resize-none rounded-xl border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Nhập tin nhắn"
              />
              <Button
                onClick={handleSubmit}
                disabled={!input.trim()}
                size="icon"
                variant="gradient"
                aria-label="Gửi tin nhắn"
              >
                <Send className="size-4" />
              </Button>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Tin nhắn sẽ đi qua cùng một bộ xử lý với voice — bạn có thể gõ lệnh giống nói.
            </p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function MessageBubble({
  turn,
  onSpeak,
}: {
  turn: ConversationTurn;
  onSpeak: (text: string) => void;
}) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        }`}
      >
        <p>{turn.content}</p>
        {!isUser && (
          <button
            onClick={() => onSpeak(turn.content)}
            className="mt-2 inline-flex items-center gap-1 text-xs opacity-70 transition-opacity hover:opacity-100"
            aria-label="Đọc to tin nhắn này"
          >
            <Volume2 className="size-3" aria-hidden /> Đọc to
          </button>
        )}
      </div>
    </div>
  );
}
