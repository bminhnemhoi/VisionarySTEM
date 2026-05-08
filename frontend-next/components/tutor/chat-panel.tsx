"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, GraduationCap, Loader2, Send, Sparkles, User, Volume2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AudioPlayer } from "@/components/audio/audio-player";
import { chat, ttsSpeakBlob, ChatResponse } from "@/lib/api";

type Bubble = {
  role: "user" | "assistant";
  content: string;
  cited_blocks?: string[];
  audio_url?: string;
};

const SUGGESTED_INITIAL = [
  "Tóm tắt tài liệu này cho tôi",
  "Giải thích công thức quan trọng nhất",
  "Cho ví dụ thực tế",
];

interface ChatPanelProps {
  documentId: string;
  documentLabel?: string;
  voiceMode?: boolean;
  rate?: string;
  pitch?: string;
}

export function ChatPanel({
  documentId,
  documentLabel,
  voiceMode = true,
  rate = "+0%",
  pitch = "+0Hz",
}: ChatPanelProps) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => crypto.randomUUID());
  const [loading, setLoading] = useState(false);
  const [followups, setFollowups] = useState<string[]>(SUGGESTED_INITIAL);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [bubbles]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setBubbles((b) => [...b, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const reply: ChatResponse = await chat(documentId, sessionId, trimmed);

      let audioUrl: string | undefined;
      if (voiceMode) {
        try {
          const blob = await ttsSpeakBlob(reply.reply_text, rate, pitch);
          audioUrl = URL.createObjectURL(blob);
        } catch {
          /* TTS optional */
        }
      }

      setBubbles((b) => [
        ...b,
        {
          role: "assistant",
          content: reply.reply_text,
          cited_blocks: reply.cited_blocks,
          audio_url: audioUrl,
        },
      ]);
      setFollowups(reply.suggested_followups.length > 0 ? reply.suggested_followups : SUGGESTED_INITIAL);
    } catch (e: any) {
      toast.error(`Lỗi gia sư: ${e.message}`);
      setBubbles((b) => [
        ...b,
        {
          role: "assistant",
          content: "Xin lỗi, tôi gặp sự cố. Vui lòng thử lại.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      bubbles.forEach((b) => {
        if (b.audio_url) URL.revokeObjectURL(b.audio_url);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
            <GraduationCap className="size-5" />
          </div>
          <div>
            <h2 className="font-bold leading-none">Gia sư AI</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {documentLabel ? `Đang học: ${documentLabel}` : `Document ID: ${documentId}`}
            </p>
          </div>
        </div>
        <Badge variant="outline">
          <Sparkles className="size-3 mr-1" /> Multi-turn
        </Badge>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div ref={scrollRef} className="space-y-4">
          {bubbles.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <div className="size-16 rounded-3xl bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center">
                <GraduationCap className="size-8 text-primary" />
              </div>
              <h3 className="text-lg font-bold">Bắt đầu cuộc hội thoại</h3>
              <p className="text-sm text-muted-foreground max-w-xs">
                Hỏi bất cứ điều gì về tài liệu — tôi sẽ giải thích bằng tiếng Việt, có ví dụ
                thực tế.
              </p>
            </div>
          )}
          <AnimatePresence>
            {bubbles.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex gap-3 ${b.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`flex size-9 shrink-0 items-center justify-center rounded-2xl ${
                    b.role === "user"
                      ? "bg-secondary text-secondary-foreground"
                      : "bg-primary text-primary-foreground"
                  }`}
                  aria-hidden
                >
                  {b.role === "user" ? <User className="size-4" /> : <Bot className="size-4" />}
                </div>
                <div className={`flex flex-col gap-2 max-w-[80%] ${b.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 leading-relaxed ${
                      b.role === "user"
                        ? "bg-secondary/15 text-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {b.content}
                  </div>
                  {b.cited_blocks && b.cited_blocks.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground">Tham chiếu:</span>
                      {b.cited_blocks.map((bid) => (
                        <Badge key={bid} variant="outline" className="font-mono text-[10px]">
                          {bid}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {b.audio_url && (
                    <AudioPlayer src={b.audio_url} autoPlay className="w-full" />
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                <Bot className="size-4" />
              </div>
              <div className="flex items-center gap-2 rounded-2xl bg-muted px-4 py-3">
                <Loader2 className="size-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Đang nghĩ...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-4 space-y-3">
        {followups.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {followups.map((f) => (
              <button
                key={f}
                onClick={() => send(f)}
                disabled={loading}
                className="text-xs rounded-full border bg-muted/40 px-3 py-1.5 hover:bg-muted transition-colors disabled:opacity-50"
              >
                {f}
              </button>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Hỏi gì về tài liệu..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            disabled={loading}
            className="flex-1 rounded-xl border bg-background px-4 py-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Câu hỏi gửi gia sư"
          />
          <Button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            aria-label="Gửi"
          >
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </Button>
        </div>
      </div>
    </Card>
  );
}
