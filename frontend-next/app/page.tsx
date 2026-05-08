"use client";

import { useEffect, useRef, useState } from "react";
import {
  Mic, MicOff, Sparkles, User, Bot, Volume2, MessageSquare,
  BookOpen, Globe, Search, FileText, Music2, Download, Languages, Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { VoiceIndicator } from "@/components/voice-indicator";
import { VoiceModeOrchestrator, type ConversationTurn } from "@/components/voice-mode-orchestrator";
import { ChatDrawer } from "@/components/chat-drawer";
import { type AnalyzeResult, ttsSpeakV2Blob } from "@/lib/api";

// PRE-ACTIVATION welcome — luôn phát mỗi lần truy cập (không phân biệt first-time hay return).
// Voice TỰ thông báo các chức năng + cách bỏ qua, không cần text trên UI.
const PRE_WELCOME_TEXT =
  "[warmly] Chào bạn, tôi là VisionarySTEM, trợ lý học STEM bằng giọng nói cho sinh viên khiếm thị. " +
  "Bạn có thể bấm phím bất kỳ bất cứ lúc nào để bỏ qua phần chào này và bắt đầu nói chuyện ngay. " +
  "Nếu bạn muốn nghe hướng dẫn các chức năng, hãy cứ tiếp tục nghe. " +
  "Tôi có thể giúp bạn theo nhiều cách. " +
  "Một, đọc và phân tích tài liệu STEM. Bạn nói tài liệu mẫu để nghe demo, hoặc thư viện để chọn từ sáu sách giáo khoa, hoặc tải file để mở file PDF từ máy bạn, hoặc tải link để dán địa chỉ web. " +
  "Hai, hỏi tôi bất cứ điều gì về toán, lý, hoá. Tôi trả lời như nói chuyện với người thật. " +
  "Ba, tìm tài liệu trên mạng. Chỉ cần nói, ví dụ, tìm bài tập chất béo hoá mười hai. Tôi sẽ search Google và tóm tắt. " +
  "Bốn, lập kế hoạch đa bước. Nói câu phức tạp như, tải vật lý và đọc đi cho tôi nghe. Tôi sẽ tự sắp xếp và làm tuần tự. " +
  "Năm, nghe biểu đồ ra âm thanh. Nói nghe biểu đồ, tôi chuyển hình vẽ thành chuỗi note nhạc theo trục Y. Đây là tính năng độc đáo cho người khiếm thị. " +
  "Sáu, xuất tài liệu ra E-Pub hoặc chữ nổi Braille. Để đọc offline trên thiết bị riêng. " +
  "Mẹo, trong lúc tôi đang trả lời, nếu chưa đúng ý bạn, hãy nhấn phím cách để dừng tôi và nói lại. " +
  "Một lần nữa, bấm phím bất kỳ ngay bây giờ để bỏ qua phần chào và bắt đầu trải nghiệm.";

// Welcome NGẮN sau khi user activate — luôn phát qua Gemini Aoede.
// Đơn giản vì user vừa nghe full intro rồi (hoặc đã skip).
// Cũng nhắc user về phím Space để dừng AI giữa câu.
const WELCOME_AFTER_ACTIVATE =
  "[warmly] Tôi đang nghe bạn. " +
  "Trong lúc tôi trả lời, nếu câu trả lời chưa đúng ý bạn, " +
  "hãy nhấn phím cách để dừng tôi và nói lại.";

/**
 * VisionarySTEM — landing voice-first ALL-IN-ONE.
 *
 * Một trang duy nhất làm tất cả:
 * - Voice landing (zero-click activate via any keypress)
 * - Real-time chat (history hiển thị trực quan)
 * - Document upload + listen + ask
 * - Bargein, continuous listening, Vietnamese natural voice
 */
export default function HomePage() {
  // Activation states:
  //   "loading"  — page just opened, pre-fetching welcome audio
  //   "ready"    — audio cached, waiting for user gesture
  //   "playing"  — pre-welcome audio is actively playing
  //   "active"   — user has interacted; switched to full voice workspace
  const [stage, setStage] = useState<"loading" | "ready" | "playing" | "active">("loading");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrlRef = useRef<string | null>(null);
  const synthUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // ============ Pre-fetch Gemini welcome audio in background (no gesture needed) ============
  // Luôn phát cùng 1 welcome mỗi lần truy cập — voice tự thông báo cách bỏ qua.
  useEffect(() => {
    let cancelled = false;

    ttsSpeakV2Blob(PRE_WELCOME_TEXT, "Aoede", "warm")
      .then((blob) => {
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        audioBlobUrlRef.current = url;
        const audio = new Audio(url);
        audio.preload = "auto";
        audioRef.current = audio;
        setStage("ready");
        // Try autoplay (often blocked but worth trying — works on rare browser configs)
        audio.play()
          .then(() => setStage("playing"))
          .catch(() => {
            // Autoplay blocked → wait for user gesture (handled by listeners below)
          });
      })
      .catch((err) => {
        console.error("[HomePage] Failed to pre-fetch welcome audio", err);
        if (!cancelled) setStage("ready");
      });

    return () => {
      cancelled = true;
      if (audioBlobUrlRef.current) {
        try { URL.revokeObjectURL(audioBlobUrlRef.current); } catch {}
      }
    };
  }, []);

  // ============ Listen for ANY user gesture to play audio + transition to active ============
  useEffect(() => {
    if (stage === "active") return;

    const tryPlayAudio = () => {
      const audio = audioRef.current;
      if (!audio) return;
      if (audio.paused && stage !== "playing") {
        audio.play().catch(() => {});
        setStage("playing");
      }
    };

    const goActive = () => {
      // Stop ALL pre-welcome playback
      try {
        if (audioRef.current && !audioRef.current.paused) audioRef.current.pause();
      } catch {}
      try {
        if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      } catch {}
      // Pre-grant mic permission via getUserMedia ngay tại user gesture.
      // Tránh race khi voiceCommands.start() gọi recognition.start() — Chrome trigger
      // permission prompt → first start có thể bị stuck đợi grant. Pre-grant fix điều đó.
      if (typeof navigator !== "undefined" && navigator.mediaDevices?.getUserMedia) {
        navigator.mediaDevices
          .getUserMedia({ audio: true })
          .then((stream) => {
            // Không cần stream — chỉ cần permission đã grant. Stop track ngay.
            stream.getTracks().forEach((t) => t.stop());
          })
          .catch((err) => {
            console.warn("[HomePage] mic permission not granted", err);
          });
      }
      setStage("active");
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      // First keypress: if audio not yet playing, START it (counts as user gesture)
      // If audio is already playing, this means user wants to skip → goActive
      if (stage === "ready" && audioRef.current?.paused) {
        tryPlayAudio();
      } else {
        goActive();
      }
    };

    const onPointer = () => {
      if (stage === "ready" && audioRef.current?.paused) {
        tryPlayAudio();
      } else {
        goActive();
      }
    };

    // ALL these count as user gesture for autoplay policy:
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("pointerdown", onPointer);
    window.addEventListener("touchstart", onPointer);

    // When the pre-welcome audio finishes playing on its own, auto-activate
    const audio = audioRef.current;
    const onEnded = () => goActive();
    audio?.addEventListener("ended", onEnded);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("pointerdown", onPointer);
      window.removeEventListener("touchstart", onPointer);
      audio?.removeEventListener("ended", onEnded);
    };
  }, [stage]);

  if (stage === "active") return <VoiceWorkspace />;
  return <PreActivation stage={stage} onManualPlay={() => audioRef.current?.play().then(() => setStage("playing")).catch(() => {})} />;
}

// ============================================================
// Pre-activation — just one big "press any key" prompt
// ============================================================

interface PreActivationProps {
  stage: "loading" | "ready" | "playing";
  onManualPlay: () => void;
}

function PreActivation({ stage, onManualPlay }: PreActivationProps) {
  // NOTE: KHÔNG dùng browser speechSynthesis fallback nữa.
  // Lý do: speechSynthesis dùng OS voice (Microsoft Cuong nam / An nữ tuỳ máy)
  // → khi chạy song song với Gemini Aoede sẽ overlap → giọng đổi nam-nữ.
  // Nếu Gemini autoplay bị block → user bấm phím/click → audio.play() qua user gesture.
  // ARIA-live announcement vẫn có cho screen reader.

  return (
    <div className="container py-16 md:py-24">
      {/* ARIA-live — screen reader tự đọc lúc page load (backup cho user dùng NVDA/VoiceOver). */}
      <div role="status" aria-live="assertive" aria-atomic="true" className="sr-only">
        Chào bạn. Đây là VisionarySTEM, trợ lý học STEM cho sinh viên khiếm thị bằng giọng nói tiếng Việt.
        Bấm phím bất kỳ để bỏ qua phần chào và bắt đầu nói chuyện ngay.
        Hoặc cứ chờ — tôi sẽ chào và hướng dẫn cách dùng bằng giọng nói.
      </div>

      <div className="mx-auto max-w-2xl text-center space-y-10">
        <Badge variant="secondary" className="inline-flex">
          <Sparkles className="mr-1 size-3" /> Cho sinh viên khiếm thị · Tiếng Việt
        </Badge>

        <div>
          <h1 className="text-5xl font-extrabold leading-tight tracking-tight md:text-7xl">
            Học STEM <br />
            <span className="text-gradient">bằng giọng nói</span>
          </h1>
          <p className="mt-6 text-2xl text-muted-foreground">
            Không cần thấy. Không cần bấm. Chỉ cần nói.
          </p>
        </div>

        {/* Big CTA — clickable to play (also any keypress works) */}
        <button
          onClick={onManualPlay}
          aria-label={
            stage === "playing"
              ? "Đang phát hướng dẫn — bấm để bỏ qua và bắt đầu"
              : "Bấm để nghe hướng dẫn và bắt đầu nói chuyện"
          }
          className="
            relative inline-flex flex-col items-center justify-center gap-4
            size-72 md:size-80 mx-auto
            rounded-full bg-gradient-to-br from-primary to-secondary text-primary-foreground
            shadow-2xl hover:shadow-primary/40 transition-all hover:scale-[1.02] active:scale-95
            focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-4
            cursor-pointer
          "
        >
          {stage === "playing" ? (
            <>
              <Volume2 className="size-24 md:size-28 animate-pulse" aria-hidden />
              <div className="text-center">
                <p className="text-2xl font-bold">Đang phát chào...</p>
                <p className="text-sm opacity-90 mt-1">Bấm phím bất kỳ để bỏ qua</p>
              </div>
            </>
          ) : stage === "loading" ? (
            <>
              <Mic className="size-24 md:size-28 opacity-50" aria-hidden />
              <div className="text-center">
                <p className="text-2xl font-bold">Đang chuẩn bị...</p>
                <p className="text-sm opacity-90 mt-1">vui lòng chờ vài giây</p>
              </div>
            </>
          ) : (
            <>
              <Mic className="size-24 md:size-28" aria-hidden />
              <div className="text-center">
                <p className="text-2xl font-bold">Bấm để nghe</p>
                <p className="text-sm opacity-90 mt-1">hoặc bấm phím bất kỳ</p>
              </div>
            </>
          )}
        </button>

        <div className="text-sm text-muted-foreground max-w-md mx-auto space-y-2">
          {stage === "playing" ? (
            <p className="text-success font-medium">
              🔊 Đang phát hướng dẫn bằng giọng nói. Bấm phím bất kỳ hoặc click nút trên để bắt đầu nói chuyện ngay.
            </p>
          ) : stage === "loading" ? (
            <p>Đang tải giọng đọc, vui lòng chờ...</p>
          ) : (
            <p>
              Bấm vào nút lớn ở giữa, hoặc bấm bất kỳ phím nào trên bàn phím (Tab, Space, Enter) để bắt đầu.
              Trình duyệt sẽ hỏi quyền micro — hãy cho phép.
            </p>
          )}
        </div>
      </div>

      {/* Feature showcase — sighted users (judges, parents) hiểu dự án ngay */}
      <FeatureShowcase />
    </div>
  );
}

// ============================================================
// Feature Showcase — chuyên nghiệp, dành cho người sáng xem được
// ============================================================
function FeatureShowcase() {
  const features = [
    {
      icon: Mic,
      title: "Voice-first",
      desc: "Nói tự nhiên tiếng Việt, AI hiểu ý — không cần học lệnh máy móc.",
      tag: "Cốt lõi",
    },
    {
      icon: BookOpen,
      title: "Đọc tài liệu STEM",
      desc: "PDF, ảnh, hoặc bài viết web. AI cắt thành block có cấu trúc, đọc bằng giọng tự nhiên.",
      tag: "Phân tích",
    },
    {
      icon: Search,
      title: "Tìm trên mạng",
      desc: "Nói \"tìm bài tập chất béo trên mạng\" — AI search Google, tóm tắt 3-5 nguồn.",
      tag: "Web Search",
    },
    {
      icon: Zap,
      title: "Multi-step AI",
      desc: "Câu phức tạp \"tải vật lý và đọc đi\" — AI lập kế hoạch, chạy đa bước.",
      tag: "Agent",
    },
    {
      icon: Globe,
      title: "Tải URL bài học",
      desc: "Wikipedia, vietjack, hocmai... AI fetch + dịch sang tiếng Việt nếu cần.",
      tag: "Universal URL",
    },
    {
      icon: FileText,
      title: "Thư viện sẵn",
      desc: "6 sách mẫu: vật lý, vi tích phân, đại số, hoá học, thống kê, sóng.",
      tag: "Library",
    },
    {
      icon: Music2,
      title: "Sonification biểu đồ",
      desc: "Biểu đồ → âm thanh: pitch tăng theo trục Y. Nghe được hình dạng đường cong.",
      tag: "Độc đáo",
    },
    {
      icon: Download,
      title: "Xuất EPUB3 + Braille",
      desc: "Tải file .epub đọc offline (Thorium Reader) hoặc Braille Unicode cho thiết bị Dot Pad.",
      tag: "Tích hợp",
    },
  ];

  return (
    <section
      aria-labelledby="features-heading"
      className="container max-w-6xl mx-auto mt-16 mb-12 px-4"
    >
      <div className="text-center mb-10">
        <Badge variant="outline" className="mb-3">
          <Sparkles className="mr-1 size-3" aria-hidden /> Chức năng dự án
        </Badge>
        <h2 id="features-heading" className="text-3xl md:text-4xl font-bold tracking-tight">
          Học STEM <span className="text-gradient">không giới hạn</span>
        </h2>
        <p className="mt-3 text-base text-muted-foreground max-w-2xl mx-auto">
          VisionarySTEM kết hợp voice-first UX, AI multimodal Gemini 2.5,
          và tích hợp ecosystem assistive (NVDA, Braille) — thiết kế riêng cho sinh viên khiếm thị Việt Nam.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map(({ icon: Icon, title, desc, tag }) => (
          <Card
            key={title}
            className="group hover:border-primary/40 hover:shadow-md transition-all duration-200"
          >
            <CardContent className="p-5 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-secondary/15 text-primary group-hover:scale-105 transition-transform">
                  <Icon className="size-5" aria-hidden />
                </div>
                <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">
                  {tag}
                </Badge>
              </div>
              <div>
                <h3 className="font-semibold text-base leading-tight mb-1">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Differentiator callout */}
      <div className="mt-10 rounded-2xl border bg-gradient-to-br from-primary/5 to-secondary/5 p-6 md:p-8">
        <div className="flex items-start gap-4">
          <div className="hidden md:flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Languages className="size-6" aria-hidden />
          </div>
          <div className="space-y-3">
            <h3 className="text-xl font-bold">
              Khác biệt với ChatGPT Voice / Gemini Live?
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="text-primary font-bold">✓</span>
                <span>
                  <b>Spatial RAG</b> — query "phần định luật ba" hay "biểu đồ ở giữa trang" — AI hiểu vị trí block trong tài liệu.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary font-bold">✓</span>
                <span>
                  <b>Tiếng Việt STEM chuẩn học thuật</b> — "F bằng m a" đọc thành "Lực bằng khối lượng nhân gia tốc", không trộn tiếng Anh.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary font-bold">✓</span>
                <span>
                  <b>Sonification + Braille export</b> — sinh viên khiếm thị nghe được biểu đồ + xuất ra thiết bị Braille. ChatGPT không có.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary font-bold">✓</span>
                <span>
                  <b>Free + Privacy</b> — chạy local, dùng Gemini free tier, không lock-in $20/tháng.
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Quick start hint */}
      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          💡 Bấm phím bất kỳ ở trên để bắt đầu trải nghiệm bằng giọng nói
        </p>
      </div>
    </section>
  );
}

// ============================================================
// Activated — voice workspace with chat history
// ============================================================

function VoiceWorkspace() {
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const announceRef = useRef<HTMLDivElement>(null);

  return (
    <VoiceModeOrchestrator
      documentId={result?.document_id ?? null}
      blocks={result?.content_blocks ?? []}
      onResultLoaded={(r) => setResult(r)}
      initialMessage={WELCOME_AFTER_ACTIVATE}
    >
      {({ state, transcript, interim, isMuted, history, start, stop, submitText }) => {
        // ARIA announcements
        useEffect(() => {
          if (announceRef.current) {
            const msgs: Record<string, string> = {
              listening: "Đang nghe.",
              processing: "Đang xử lý.",
              speaking: "Đang trả lời.",
              muted: "Micro đã tắt.",
              idle: "Sẵn sàng.",
            };
            announceRef.current.textContent = msgs[state] ?? "";
          }
        }, [state]);

        return (
          <div className="container py-8 md:py-12">
            <div ref={announceRef} role="status" aria-live="polite" aria-atomic="true" className="sr-only" />

            <div className="mx-auto max-w-3xl space-y-6">
              {/* Status indicator (sticky top so always visible) */}
              <div className="sticky top-20 z-30 -mx-4 px-4 py-3 bg-background/85 backdrop-blur rounded-2xl border shadow-sm">
                <div className="flex flex-col items-center gap-3">
                  <VoiceIndicator
                    state={state}
                    transcript={interim || (state === "listening" ? transcript : undefined)}
                    variant="banner"
                    className="w-full"
                  />
                  {isMuted ? (
                    <Button size="default" variant="gradient" onClick={start}>
                      <Mic className="size-4" /> Bật lại micro
                    </Button>
                  ) : (
                    <button
                      onClick={stop}
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                      aria-label="Tắt micro tạm thời"
                    >
                      <MicOff className="size-3" /> Tắt mic tạm thời
                    </button>
                  )}
                </div>
              </div>

              {/* Document loaded? Show summary */}
              {result && (
                <Card className="bg-primary/5 border-primary/20">
                  <CardContent className="p-4 flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <p className="text-xs text-muted-foreground">Đang học</p>
                      <p className="font-bold">{result.document_metadata.filename}</p>
                    </div>
                    <Badge variant="outline">
                      {result.content_blocks.length} phần · {result.document_metadata.total_pages} trang
                    </Badge>
                  </CardContent>
                </Card>
              )}

              {/* Chat history — visible conversation */}
              <ChatHistory history={history} state={state} interim={interim} />

              {/* Quick suggestions when history empty */}
              {history.length === 0 && state !== "speaking" && (
                <Card className="bg-muted/40 border-dashed">
                  <CardContent className="p-6 space-y-3 text-center">
                    <p className="text-sm text-muted-foreground">Bạn có thể nói:</p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {[
                        "Tài liệu mẫu",
                        "Tải file",
                        "Newton là ai?",
                        "Giúp đỡ",
                        "Làm sao để học?",
                      ].map((cmd) => (
                        <button
                          key={cmd}
                          onClick={() => submitText(cmd)}
                          className="text-sm rounded-full border bg-background px-4 py-2 hover:bg-primary hover:text-primary-foreground transition-colors"
                        >
                          {cmd}
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground pt-2">
                      Hoặc đặt bất kỳ câu hỏi nào — tôi sẽ trả lời như một người thật.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* FAB to open chat drawer (Phase 1: text fallback when voice unavailable) */}
            <button
              onClick={() => setChatOpen(true)}
              aria-label="Mở khung chat (Ctrl + /)"
              title="Mở chat (Ctrl + /)"
              className="fixed bottom-6 right-6 z-30 flex size-14 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-lg transition-transform hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-2"
            >
              <MessageSquare className="size-6" aria-hidden />
            </button>

            <ChatDrawer
              open={chatOpen}
              onOpenChange={setChatOpen}
              history={history}
              submitText={submitText}
            />
          </div>
        );
      }}
    </VoiceModeOrchestrator>
  );
}

// ============================================================
// Chat history bubbles
// ============================================================

function ChatHistory({
  history,
  state,
  interim,
}: {
  history: ConversationTurn[];
  state: string;
  interim: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [history.length, state]);

  if (history.length === 0 && !interim) return null;

  return (
    <div className="space-y-3" role="log" aria-live="polite" aria-relevant="additions">
      <AnimatePresence initial={false}>
        {history.map((turn, i) => (
          <motion.div
            key={`${turn.timestamp}-${i}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={`flex gap-3 ${turn.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`flex size-9 shrink-0 items-center justify-center rounded-2xl ${
                turn.role === "user"
                  ? "bg-secondary text-secondary-foreground"
                  : "bg-primary text-primary-foreground"
              }`}
              aria-hidden
            >
              {turn.role === "user" ? <User className="size-4" /> : <Bot className="size-4" />}
            </div>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 leading-relaxed ${
                turn.role === "user" ? "bg-secondary/15" : "bg-muted"
              }`}
            >
              <span className="text-[10px] text-muted-foreground block mb-1">
                {turn.role === "user" ? "Bạn" : "Trợ lý"}
              </span>
              <p>{turn.content}</p>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Live interim user speech (while user is talking) */}
      {state === "listening" && interim && (
        <div className="flex gap-3 flex-row-reverse opacity-60">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-2xl bg-secondary/40 text-secondary-foreground">
            <User className="size-4" />
          </div>
          <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-secondary/10 italic">
            {interim}
            <span className="ml-1 inline-block w-2 h-4 bg-secondary animate-pulse rounded-sm align-middle" />
          </div>
        </div>
      )}

      {/* Show "thinking" indicator while processing */}
      {state === "processing" && (
        <div className="flex gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
            <Bot className="size-4" />
          </div>
          <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-muted">
            <span className="text-muted-foreground italic">Đang nghĩ...</span>
          </div>
        </div>
      )}

      <div ref={scrollRef} aria-hidden />
    </div>
  );
}
