"use client";

/**
 * VoiceModeOrchestrator — heart of voice-first UX.
 *
 * State machine:
 *   idle → listening (user speaks) → processing (intent dispatched, awaiting reply)
 *        → speaking (TTS phát) → idle | listening (continuous loop)
 *
 * Handles:
 * - Continuous mic listen + VAD (via useVoiceCommands)
 * - Bargein: user nói → dừng TTS, huỷ chat stream
 * - Intent dispatch: route mỗi VoiceIntent → action thực tế
 * - File upload trigger via voice
 * - Auto-TTS reply
 *
 * Note: phần lớn logic đặt ở đây vì đây là single source of truth cho voice flow.
 * Component không render UI nặng — chỉ trả callbacks + state cho parent.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  AnalyzeResult,
  ContentBlock,
  analyzeFile,
  mockAnalyze,
  ttsBlockUrl,
  ttsSpeakV2Blob,
  generalAssist,
  loadFromLibrary,
  analyzeUrl,
  webSearch,
  agentRun,
  exportEpub3,
  exportBraille,
  sonifyBlock,
  triggerDownload,
  type WebSource,
} from "@/lib/api";
import { UrlInputDialog } from "@/components/url-input-dialog";
import { LIBRARY_INTRO_TEXT, LIBRARY_TITLES } from "@/components/voice-mode-orchestrator.constants";
import { streamChat } from "@/lib/chat-stream";
import { useVoiceCommands } from "@/lib/use-voice-commands";
import { parseVoiceCommand, type VoiceIntent, getHelpText } from "@/lib/voice-command-grammar";
import { useAudioStore, stopAllAudio } from "@/lib/audio-store";
import type { VoiceState } from "@/components/voice-indicator";

/** One conversation turn — for visible chat history. */
export type ConversationTurn = {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
};

interface OrchestratorProps {
  /** Document ID to converse about (null = no doc loaded yet, only mock/upload commands work). */
  documentId: string | null;
  blocks: ContentBlock[];
  /** Notify parent when result loaded via voice command. */
  onResultLoaded?: (result: AnalyzeResult) => void;
  /** Optional welcome message — spoken on first mount via orchestrator's speak() (auto-restarts mic). */
  initialMessage?: string;
  /** Render-prop: passes state + helpers to UI. */
  children: (props: {
    state: VoiceState;
    transcript: string;
    interim: string;
    lastSpoken: string;
    isMuted: boolean;
    history: ConversationTurn[];
    start: () => void;
    stop: () => void;
    triggerFileInput: () => void;
    onFilePicked: (f: File) => Promise<void>;
    submitText: (text: string) => void;
  }) => React.ReactNode;
}

export function VoiceModeOrchestrator({
  documentId,
  blocks,
  onResultLoaded,
  initialMessage,
  children,
}: OrchestratorProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [lastSpoken, setLastSpoken] = useState<string>("");
  const [history, setHistory] = useState<ConversationTurn[]>([]);
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  // Pending file picker: voice "tải file" prepares + asks user to press any key
  // (browser security cấm programmatic .click() ngoài user gesture)
  const [pendingFilePicker, setPendingFilePicker] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const abortChatRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string>(typeof crypto !== "undefined" ? crypto.randomUUID() : "session_1");
  const currentBlockIndexRef = useRef<number>(0);
  const initialMessagePlayedRef = useRef(false);
  const filePickerTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const focusBlockId = useAudioStore((s) => s.currentBlockId);

  // Helper to append history entry
  const addToHistory = useCallback((role: "user" | "assistant", content: string) => {
    setHistory((h) => [...h, { role, content, timestamp: Date.now() }]);
  }, []);

  /**
   * Speak text via Gemini TTS. Resolves AFTER audio playback ends.
   * Auto-restarts mic listener afterwards (Chrome auto-pauses mic during audio).
   * Forward declared — set after voiceCommands hook is created (see below).
   *
   * GUARD: Mỗi call lấy generation id mới. Nếu speak() khác fire trước khi cái cũ
   * xong (ví dụ duplicate dispatch race), generation cũ bị abort → chỉ 1 audio phát.
   */
  const forceRestartMicRef = useRef<(() => void) | null>(null);
  // Pause/resume mic refs — pause TRƯỚC khi TTS phát, resume SAU khi xong.
  // Tránh AI's own voice leak vào mic → self-dispatch loop.
  const pauseListeningRef = useRef<(() => void) | null>(null);
  const resumeListeningRef = useRef<(() => void) | null>(null);
  // Mute/unmute refs — user-facing tắt mic, KHÁC pause/resume nội bộ.
  const muteRef = useRef<(() => void) | null>(null);
  const unmuteRef = useRef<(() => void) | null>(null);
  const speakGenRef = useRef(0);
  // Background announcement queue: nếu đang speak (TTS đang phát), defer announcement.
  // Khi audio hiện tại end → cleanup tự fire announcement này. Tránh 2 voice chồng.
  const pendingAnnouncementRef = useRef<string | null>(null);
  // Self-reference cho speak() — cleanup setTimeout cần gọi lại speak để fire pending
  const speakRef = useRef<((text: string) => Promise<void>) | null>(null);
  const speak = useCallback(async (text: string): Promise<void> => {
    if (!text || text.trim().length === 0) return;
    const myGen = ++speakGenRef.current;

    setState("speaking");
    setLastSpoken(text);
    addToHistory("assistant", text);

    // BẮT BUỘC abort audio cũ — kể cả từ Audio orphan trước đó (block playback)
    if (ttsAudioRef.current) {
      try { ttsAudioRef.current.pause(); } catch {}
      try { URL.revokeObjectURL(ttsAudioRef.current.src); } catch {}
      ttsAudioRef.current = null;
    }
    stopAllAudio();

    // PAUSE MIC trước khi TTS phát → AI voice không leak vào mic → tránh self-dispatch loop
    pauseListeningRef.current?.();

    try {
      const blob = await ttsSpeakV2Blob(text, "Aoede", "auto");
      // Nếu speak khác đã fire sau ta → bỏ — đừng phát stale audio
      // (speak mới đã tự pause mic, không cần ta resume — tránh race)
      if (myGen !== speakGenRef.current) return;

      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.dataset.label = "Hệ thống";
      // Race case (speak khác chen vào giữa fetch blob) đã cover bởi gen check ở line 132
      ttsAudioRef.current = audio;

      // Wait for audio to finish playing (or be paused for bargein)
      await new Promise<void>((resolve) => {
        let resolved = false;
        const cleanup = () => {
          if (resolved) return;
          resolved = true;
          try { URL.revokeObjectURL(url); } catch {}
          // Chỉ clear ref nếu vẫn là generation hiện tại
          if (myGen === speakGenRef.current) {
            ttsAudioRef.current = null;
            // RESUME MIC ngay sau audio xong — user có thể nói liền
            resumeListeningRef.current?.();
            // Fire pending background announcement nếu có (defer until idle)
            const pending = pendingAnnouncementRef.current;
            if (pending) {
              pendingAnnouncementRef.current = null;
              // Small delay để audio cleanup hoàn tất
              setTimeout(() => {
                speakRef.current?.(pending).catch(() => {});
              }, 250);
            }
          }
          resolve();
        };
        audio.onended = cleanup;
        audio.onpause = () => {
          // Bargein: user spoke → audio paused → also resolve
          if (audio.currentTime < audio.duration) cleanup();
        };
        audio.onerror = () => cleanup();
        audio.play().catch(() => cleanup());
      });
    } catch (e) {
      console.error("[orchestrator] speak failed", e);
    } finally {
      // Chỉ update state nếu vẫn là generation hiện tại (tránh ghi đè state của speak mới)
      if (myGen === speakGenRef.current) {
        setState((s) => (s === "speaking" ? "listening" : s));
        // Đảm bảo mic luôn resume — kể cả error path / gen mismatch
        // (cleanup đã resume khi audio end thành công; chỗ này cover error & early return)
        resumeListeningRef.current?.();
      }
    }
  }, [addToHistory]);

  // Keep speakRef in sync — for self-reference in cleanup setTimeout
  useEffect(() => {
    speakRef.current = speak;
  }, [speak]);

  // ============ Bargein: user starts talking → stop TTS + cancel chat ============
  const handleSpeechStart = useCallback(() => {
    // User barges in → clear any pending announcement (user wants to speak now)
    pendingAnnouncementRef.current = null;
    if (ttsAudioRef.current && !ttsAudioRef.current.paused) {
      ttsAudioRef.current.pause();
    }
    stopAllAudio();
    if (abortChatRef.current) {
      abortChatRef.current.abort();
      abortChatRef.current = null;
    }
  }, []);

  // ============ Block helpers ============
  const findBlock = useCallback(
    (id: string | null): ContentBlock | null => {
      if (!id) return null;
      return blocks.find((b) => b.id === id) ?? null;
    },
    [blocks],
  );

  // ============ Background analyze helper ============
  // Fire-and-forget: dispatch intent return ngay, analyze chạy ngầm.
  // User có thể hỏi/làm gì khác trong lúc đợi. Khi xong → ANNOUNCE THÔNG MINH:
  //  - Nếu đang có TTS phát (AI đang trả lời câu hỏi user) → defer, fire khi audio xong
  //  - Nếu idle → speak ngay
  // → KHÔNG BAO GIỜ 2 voice chồng nhau.
  const announceWhenIdle = useCallback(
    (text: string) => {
      const audio = ttsAudioRef.current;
      const isBusy = audio && !audio.paused && !audio.ended;
      if (isBusy) {
        // Defer — speak()'s cleanup sẽ fire khi audio hiện tại xong
        pendingAnnouncementRef.current = text;
      } else {
        speak(text).catch(() => {});
      }
    },
    [speak],
  );

  const startBackgroundAnalyze = useCallback(
    (promise: Promise<AnalyzeResult>, friendlyName: string) => {
      promise
        .then((r) => {
          onResultLoaded?.(r);
          sessionStorage.setItem("vs_last_doc_id", r.document_id);
          sessionStorage.setItem("vs_last_doc_name", r.document_metadata.filename);
          const nBlocks = r.content_blocks.length;
          announceWhenIdle(
            `Đã sẵn sàng tài liệu ${friendlyName}, có ${nBlocks} phần. ` +
            `Bạn có thể nói "đọc đi" để bắt đầu nghe, "tóm tắt" để nghe tổng quan, hoặc hỏi bất cứ điều gì.`,
          );
        })
        .catch((e: any) => {
          console.error("[orchestrator] background analyze failed", e);
          announceWhenIdle(
            `Xin lỗi, không tải được tài liệu ${friendlyName}. ` +
            `Bạn có thể thử lại, hoặc chọn cách khác.`,
          );
          toast.error(`Lỗi tải tài liệu: ${e.message ?? e}`);
        });
    },
    [onResultLoaded, announceWhenIdle],
  );

  // ============ Intent dispatch ============
  const dispatchIntent = useCallback(
    async (intent: VoiceIntent, raw: string) => {
      console.debug("[orchestrator] intent:", intent, "raw:", raw);
      // Add user utterance to visible history (skip pure control commands)
      const isControlCommand = ["mute", "unmute", "stop_all", "pause", "play", "resume", "seek", "next_block", "prev_block"].includes(intent.kind);
      if (!isControlCommand) {
        addToHistory("user", raw);
      }
      setState("processing");

      switch (intent.kind) {
        case "load_mock": {
          // Mock load nhanh (~1s) — không cần background pattern
          await speak("Đang tải tài liệu mẫu.");
          startBackgroundAnalyze(mockAnalyze(), "mẫu Định luật Newton");
          break;
        }

        case "upload_file": {
          // Browser security: programmatic .click() trên <input type="file"> CHỈ chạy
          // trong user gesture chain. Voice → speech recognition không phải gesture.
          // Workaround: prompt user bấm phím bất kỳ → keydown handler (= user gesture)
          // sẽ trigger click(). Set pending flag → effect bên dưới đăng ký listener.
          setPendingFilePicker(true);
          if (filePickerTimeoutRef.current) clearTimeout(filePickerTimeoutRef.current);
          filePickerTimeoutRef.current = setTimeout(() => {
            setPendingFilePicker(false);
            speak("Đã hết thời gian chờ. Nói tải file lại nếu vẫn muốn mở hộp thoại.").catch(() => {});
          }, 30000);
          await speak(
            "Tôi đã sẵn sàng mở hộp thoại chọn file PDF từ máy bạn. " +
              "Hãy bấm phím bất kỳ trên bàn phím ngay bây giờ. " +
              "Hỗ trợ PDF, P-N-G, J-P-G, tối đa hai mươi mê-ga-bai.",
          );
          break;
        }

        case "play":
        case "resume": {
          if (blocks.length === 0) {
            await speak("Chưa có tài liệu. Hãy nói 'tài liệu mẫu' hoặc 'mở file'.");
            break;
          }
          // Play current or first block via Audio element
          const idx = currentBlockIndexRef.current;
          const block = blocks[idx];
          if (!block || !documentId) {
            await speak("Không tìm thấy nội dung để phát.");
            break;
          }
          stopAllAudio();
          const url = ttsBlockUrl(block.id, documentId);
          const audio = new Audio(url);
          audio.dataset.label = `Block ${block.id}`;
          audio.dataset.blockId = block.id;
          ttsAudioRef.current = audio;
          setState("speaking");
          audio.onended = () => {
            // Auto-advance to next block
            currentBlockIndexRef.current = idx + 1;
            if (currentBlockIndexRef.current < blocks.length) {
              // Small pause then continue
              setTimeout(() => dispatchIntent({ kind: "play" }, "auto").catch(() => {}), 400);
            } else {
              setState("listening");
              speak("Đã đọc xong tài liệu.");
            }
          };
          audio.play().catch(() => setState("listening"));
          break;
        }

        case "pause": {
          if (ttsAudioRef.current) ttsAudioRef.current.pause();
          stopAllAudio();
          setState("listening");
          break;
        }

        case "replay_block": {
          if (ttsAudioRef.current) {
            ttsAudioRef.current.currentTime = 0;
            ttsAudioRef.current.play().catch(() => {});
            setState("speaking");
          } else {
            await dispatchIntent({ kind: "play" }, "replay");
          }
          break;
        }

        case "seek": {
          if (ttsAudioRef.current) {
            const a = ttsAudioRef.current;
            a.currentTime = Math.max(0, Math.min((a.duration || 9999), a.currentTime + intent.deltaSeconds));
            const direction = intent.deltaSeconds < 0 ? "lùi" : "tới";
            await speak(`Đã tua ${direction} ${Math.abs(intent.deltaSeconds)} giây.`);
          } else {
            await speak("Hiện không có audio đang phát để tua.");
          }
          break;
        }

        case "next_block":
        case "prev_block": {
          const delta = intent.kind === "next_block" ? 1 : -1;
          const newIdx = Math.max(0, Math.min(blocks.length - 1, currentBlockIndexRef.current + delta));
          currentBlockIndexRef.current = newIdx;
          await dispatchIntent({ kind: "play" }, intent.kind);
          break;
        }

        case "filter_blocks": {
          const filtered = blocks.filter((b) => b.type === intent.type);
          if (filtered.length === 0) {
            await speak(`Không có ${typeLabelVi(intent.type)} nào trong tài liệu.`);
            break;
          }
          await speak(`Có ${filtered.length} ${typeLabelVi(intent.type)}. Tôi sẽ đọc lần lượt.`);
          // Play first matched block; auto-advance handled in 'play' intent
          const firstMatchedIdx = blocks.findIndex((b) => b.id === filtered[0].id);
          currentBlockIndexRef.current = firstMatchedIdx;
          await dispatchIntent({ kind: "play" }, "filter");
          break;
        }

        case "ask_focus_block":
        case "ask_simpler":
        case "ask_example":
        case "free_chat":
        case "summarize": {
          // No-doc fallback: use general assistant for free_chat questions
          if (!documentId) {
            if (intent.kind === "free_chat") {
              const q = (intent as { kind: "free_chat"; question: string }).question;
              try {
                // Pass sessionId để backend nhớ history → không re-introduce mỗi câu
                const r = await generalAssist(q, sessionIdRef.current);
                await speak(r.reply_text);
              } catch {
                await speak(
                  "Xin lỗi, gặp sự cố. Hãy thử nói 'tài liệu mẫu' để bắt đầu, hoặc 'giúp đỡ'.",
                );
              }
              break;
            }
            // Other intents (ask_simpler/ask_example/summarize/ask_focus_block) need a doc
            await speak(
              "Chưa có tài liệu. Hãy nói 'tài liệu mẫu' để bắt đầu, hoặc 'tải file' để mở file của bạn.",
            );
            break;
          }
          // Pause TTS during chat
          if (ttsAudioRef.current) ttsAudioRef.current.pause();
          stopAllAudio();

          const message =
            intent.kind === "ask_simpler"
              ? "Giải thích phần đang nghe đơn giản hơn."
              : intent.kind === "ask_example"
                ? "Cho ví dụ thực tế đời sống về phần này."
                : intent.kind === "summarize"
                  ? "Tóm tắt tài liệu trong 4-5 câu."
                  : intent.kind === "ask_focus_block"
                    ? "Phần này nói gì? Giải thích ngắn gọn."
                    : (intent as { kind: "free_chat"; question: string }).question;

          // Stream chat reply, accumulate, then speak ENTIRE reply at end
          // (Streaming → speak partial would be confusing for blind users)
          abortChatRef.current = new AbortController();
          let accumulated = "";
          try {
            for await (const evt of streamChat(
              {
                document_id: documentId,
                session_id: sessionIdRef.current,
                message,
                focus_block_id: focusBlockId ?? undefined,
              },
              abortChatRef.current.signal,
            )) {
              if (evt.event === "token") {
                accumulated = evt.data.accumulated;
              } else if (evt.event === "done") {
                accumulated = evt.data.reply_text;
              } else if (evt.event === "error") {
                throw new Error(evt.data.detail);
              }
            }
            await speak(accumulated);
          } catch (e: any) {
            if (e?.name !== "AbortError") {
              await speak("Xin lỗi, gặp lỗi khi trả lời. Bạn thử lại nhé.");
            }
          } finally {
            abortChatRef.current = null;
          }
          break;
        }

        case "repeat_last": {
          if (lastSpoken) {
            await speak(lastSpoken);
          } else {
            await speak("Chưa có gì để nhắc lại.");
          }
          break;
        }

        case "help": {
          await speak(getHelpText());
          break;
        }

        case "mute": {
          // Mute TRƯỚC (set isMutedRef=true) — sau speak, resumeListening sẽ skip
          // vì check isMutedRef. Nếu speak trước mute, có khoảng giây mic bật giữa
          // resume và mute — user có thể nói nhầm vào.
          muteRef.current?.();
          await speak(
            "Đã tắt micro. Để bật lại, nói 'bật mic' không có tác dụng vì tôi không nghe — " +
            "bạn cần dùng tay click nút mic ở góc dưới phải, hoặc reload trang.",
          );
          break;
        }

        case "unmute": {
          // Unmute TRƯỚC khi speak để mic active sẵn
          unmuteRef.current?.();
          await speak("Đã bật micro. Bạn cứ nói.");
          break;
        }

        case "stop_all": {
          if (ttsAudioRef.current) ttsAudioRef.current.pause();
          if (abortChatRef.current) abortChatRef.current.abort();
          stopAllAudio();
          setState("listening");
          break;
        }

        case "skip_welcome": {
          // Cut current TTS (welcome or any speak) without speaking anything new
          if (ttsAudioRef.current) {
            try { ttsAudioRef.current.pause(); } catch {}
          }
          stopAllAudio();
          setState("listening");
          // Force restart mic (welcome speak() probably hasn't reached its forceRestart)
          forceRestartMicRef.current?.();
          break;
        }

        case "library_browse": {
          await speak(LIBRARY_INTRO_TEXT);
          break;
        }

        case "library_load": {
          const title = LIBRARY_TITLES[intent.slug] ?? intent.slug;
          await speak(
            `Đang tải ${title}. Trong lúc đợi, bạn có thể hỏi tôi bất cứ điều gì khác — ` +
            `khi tài liệu sẵn sàng tôi sẽ báo bạn ngay.`,
          );
          startBackgroundAnalyze(loadFromLibrary(intent.slug), title);
          break;
        }

        case "upload_url": {
          await speak(
            "Tôi mở ô dán link. Bấm Control V để dán địa chỉ web, sau đó bấm Enter để xác nhận. " +
            "Hỗ trợ PDF, ảnh, hoặc bài viết học liệu như Wikipedia hay vietjack. " +
            "Bấm Escape để huỷ.",
          );
          setUrlDialogOpen(true);
          break;
        }

        case "agent_run": {
          // Phase 3 — Multi-step planner + executor SSE
          const req = intent.request.trim();
          await speak(
            `Tôi đang lập kế hoạch để xử lý yêu cầu của bạn. Đợi mình vài giây.`,
          );
          abortChatRef.current = new AbortController();
          try {
            for await (const evt of agentRun(req, abortChatRef.current.signal)) {
              if (evt.event === "plan_ready") {
                // Narrate plan overview trước khi chạy
                await speak(evt.data.plan_overview);
              } else if (evt.event === "step_start") {
                await speak(evt.data.narration);
              } else if (evt.event === "step_done") {
                await speak(evt.data.summary);
              } else if (evt.event === "step_error") {
                await speak(
                  `Xin lỗi, bước ${evt.data.index + 1} gặp lỗi. Tôi sẽ dừng lại.`,
                );
              } else if (evt.event === "plan_done") {
                await speak(evt.data.summary_narration);
              }
            }
          } catch (e: any) {
            if (e?.name !== "AbortError") {
              console.error("[orchestrator] agent_run failed", e);
              await speak(
                "Xin lỗi, kế hoạch bị lỗi giữa chừng. Bạn thử lại nhé.",
              );
            }
          } finally {
            abortChatRef.current = null;
          }
          break;
        }

        case "export_epub": {
          if (!documentId) {
            await speak(
              "Chưa có tài liệu nào để xuất. Hãy nói 'tài liệu mẫu' hoặc tải file trước.",
            );
            break;
          }
          await speak("Đang tạo file E-Pub. Đợi mình một chút.");
          try {
            const blob = await exportEpub3(documentId);
            const fname = blocks.length > 0 && documentId
              ? `${documentId}.epub`
              : "visionarystem.epub";
            triggerDownload(blob, fname);
            await speak(
              "Đã tải file E-Pub về máy bạn. " +
              "Mở bằng Thorium Reader hoặc iBooks để đọc offline. " +
              "File hỗ trợ MathML — screen reader đọc đúng công thức toán.",
            );
          } catch (e: any) {
            console.error("[orchestrator] export_epub failed", e);
            await speak("Xin lỗi, không xuất được E-Pub. Bạn thử lại nhé.");
          }
          break;
        }

        case "export_braille": {
          if (!documentId) {
            await speak(
              "Chưa có tài liệu nào để xuất. Hãy nói 'tài liệu mẫu' hoặc tải file trước.",
            );
            break;
          }
          await speak("Đang tạo file chữ nổi Braille. Đợi mình một chút.");
          try {
            const blob = await exportBraille(documentId);
            triggerDownload(blob, `${documentId}_braille.txt`);
            await speak(
              "Đã tải file chữ nổi về máy bạn. " +
              "Có thể copy vào thiết bị BrailleSense, Dot Pad, " +
              "hoặc in qua máy in chữ nổi để đọc trên giấy.",
            );
          } catch (e: any) {
            console.error("[orchestrator] export_braille failed", e);
            await speak("Xin lỗi, không xuất được chữ nổi. Bạn thử lại nhé.");
          }
          break;
        }

        case "sonify_chart": {
          if (!documentId || blocks.length === 0) {
            await speak("Chưa có tài liệu nào. Hãy tải tài liệu trước.");
            break;
          }
          // Tìm chart block: ưu tiên block_index nếu user chỉ định, else first chart
          let target = null;
          if (intent.block_index !== undefined && intent.block_index >= 1) {
            target = blocks[intent.block_index - 1] ?? null;
          }
          if (!target) {
            target = blocks.find((b) => b.type === "chart") ?? null;
          }
          if (!target) {
            await speak(
              "Tài liệu này không có biểu đồ. " +
              "Sonification chỉ hoạt động với block kiểu biểu đồ.",
            );
            break;
          }
          await speak(
            "Đang chuyển biểu đồ thành âm thanh. " +
            "Bạn nghe pitch tăng theo giá trị Y trục dọc.",
          );
          try {
            // PAUSE mic trong khi sonify audio phát (giống TTS)
            pauseListeningRef.current?.();
            const blob = await sonifyBlock(documentId, target.id);
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            await new Promise<void>((resolve) => {
              audio.onended = () => {
                URL.revokeObjectURL(url);
                resolve();
              };
              audio.onerror = () => {
                URL.revokeObjectURL(url);
                resolve();
              };
              audio.play().catch(() => resolve());
            });
            // RESUME mic sau khi audio xong
            resumeListeningRef.current?.();
            await speak("Đã phát xong. Bạn cảm nhận được hình dạng biểu đồ qua âm thanh chứ?");
          } catch (e: any) {
            resumeListeningRef.current?.();
            console.error("[orchestrator] sonify_chart failed", e);
            await speak("Xin lỗi, không sonify được biểu đồ này.");
          }
          break;
        }

        case "web_search": {
          // Phase 2 — Gemini grounding với Google Search
          const query = intent.query.trim();
          await speak(
            `Tôi tìm trên mạng về ${query}. Đợi mình vài giây.`,
          );
          try {
            const result = await webSearch(query, 5);
            // Add to history dưới dạng assistant message với summary + sources
            // Speak summary trước, sau đó liệt kê sources ngắn gọn
            const sourcesPreview =
              result.sources.length > 0
                ? " Tôi tìm được " +
                  result.sources.length +
                  " nguồn: " +
                  result.sources
                    .slice(0, 3)
                    .map((s: WebSource, i: number) => `${i + 1}, ${s.title}`)
                    .join(". ") +
                  ". Bạn muốn tôi phân tích sâu nguồn nào, hoặc tìm chủ đề khác?"
                : " Hiện tôi không thấy nguồn cụ thể. Bạn thử từ khoá khác nhé.";
            await speak(result.summary + sourcesPreview);
          } catch (e: any) {
            console.error("[orchestrator] web_search failed", e);
            await speak(
              `Xin lỗi, tôi không tìm được thông tin về ${query}. ` +
              `Bạn thử lại hoặc đổi từ khoá nhé.`,
            );
          }
          break;
        }

        case "upload_ask_source": {
          await speak(
            "Bạn muốn tải tài liệu từ máy của bạn, hay từ một link mạng? " +
            "Nói 'từ máy' để mở file PDF trên máy bạn. " +
            "Nói 'từ link' để dán địa chỉ URL. " +
            "Hoặc nói 'thư viện' để chọn từ sáu sách mẫu có sẵn.",
          );
          break;
        }
      }

      // Default: return to listening unless still speaking
      setState((s) => (s === "speaking" ? s : "listening"));
    },
    [blocks, documentId, focusBlockId, lastSpoken, onResultLoaded, speak, addToHistory],
  );

  // ============ Voice command hook ============
  const voiceCommands = useVoiceCommands({
    onIntent: dispatchIntent,
    onSpeechStart: handleSpeechStart,
    onListening: (active) => {
      // Only update state if not currently processing/speaking
      setState((s) => (s === "processing" || s === "speaking" ? s : active ? "listening" : s));
    },
    silenceMs: 500,
    autoStart: false,
  });

  // Wire forceRestart so speak() can call it after audio ends
  useEffect(() => {
    forceRestartMicRef.current = voiceCommands.forceRestart;
  }, [voiceCommands.forceRestart]);

  // Wire pause/resume — speak() pauses mic during TTS, resumes after
  useEffect(() => {
    pauseListeningRef.current = voiceCommands.pauseListening;
    resumeListeningRef.current = voiceCommands.resumeListening;
    muteRef.current = voiceCommands.mute;
    unmuteRef.current = voiceCommands.unmute;
  }, [
    voiceCommands.pauseListening,
    voiceCommands.resumeListening,
    voiceCommands.mute,
    voiceCommands.unmute,
  ]);

  // Sync mute state to indicator
  useEffect(() => {
    if (voiceCommands.isMuted) setState("muted");
  }, [voiceCommands.isMuted]);

  // ============ Space key bargein — dừng AI speak khi user nhấn Space ============
  // Cho user khả năng can thiệp lúc AI đang nói (ví dụ AI hiểu sai → dừng để nói lại).
  // KHÔNG conflict với pendingFilePicker handler (file picker chỉ active khi pending=true).
  useEffect(() => {
    const onSpaceBargein = (e: KeyboardEvent) => {
      // Skip nếu pending file picker (handler khác xử lý mọi phím cho mục đích đó)
      if (pendingFilePicker) return;
      // Skip nếu đang gõ trong input/textarea
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;
      // Chỉ bắt phím Space
      if (e.key !== " " && e.code !== "Space") return;

      // Chỉ act khi AI đang thực sự phát audio
      const audio = ttsAudioRef.current;
      if (audio && !audio.paused && !audio.ended) {
        e.preventDefault();
        audio.pause(); // → onpause → cleanup → resume mic
        // Clear pending background announcement (user muốn nói tiếp, không cần thông báo)
        pendingAnnouncementRef.current = null;
        // Cancel any in-flight chat stream
        if (abortChatRef.current) {
          abortChatRef.current.abort();
          abortChatRef.current = null;
        }
      }
    };
    window.addEventListener("keydown", onSpaceBargein);
    return () => window.removeEventListener("keydown", onSpaceBargein);
  }, [pendingFilePicker]);

  // Speak welcome on first mount (only ONE time)
  useEffect(() => {
    if (initialMessage && !initialMessagePlayedRef.current) {
      initialMessagePlayedRef.current = true;
      // Start mic FIRST so it's ready when welcome ends
      voiceCommands.start();
      // Speak welcome — speak() resolves after audio ends, then auto forceRestart
      speak(initialMessage).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage]);

  // ============ File picker user-gesture handoff ============
  // Khi `pendingFilePicker=true`, đăng ký global keydown listener.
  // User bấm phím bất kỳ → keydown handler (= USER GESTURE) → trigger fileInput.click()
  // → OS dialog mở. Cần phím nào cũng được vì sinh viên khiếm thị không thấy phím cụ thể.
  useEffect(() => {
    if (!pendingFilePicker) return;

    const onKey = (e: KeyboardEvent) => {
      // Skip nếu user đang gõ trong input/textarea (chat drawer)
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;
      // Skip modifier-only keys (user chưa thực sự bấm phím cuối)
      if (["Shift", "Control", "Alt", "Meta", "CapsLock"].includes(e.key)) return;

      e.preventDefault();
      // Clear pending state TRƯỚC click() để useEffect cleanup tránh double-fire
      setPendingFilePicker(false);
      if (filePickerTimeoutRef.current) {
        clearTimeout(filePickerTimeoutRef.current);
        filePickerTimeoutRef.current = null;
      }
      // Trigger OS file dialog (synchronous trong user gesture → browser cho phép)
      try {
        fileInputRef.current?.click();
      } catch (err) {
        console.error("[orchestrator] file picker click failed", err);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [pendingFilePicker]);

  // ============ File picker handler ============
  // Background analyze: speak ngay xác nhận chọn file + invitation hỏi gì khác,
  // analyze chạy nền, khi xong → speak announcement.
  const onFilePicked = useCallback(
    async (file: File) => {
      await speak(
        `Đã chọn file ${file.name}. ` +
        `Tôi đang phân tích, việc này có thể mất một chút. ` +
        `Trong lúc đợi, bạn có thể hỏi tôi bất cứ điều gì khác — ` +
        `khi phân tích xong tôi sẽ báo bạn ngay.`,
      );
      startBackgroundAnalyze(analyzeFile(file), file.name);
    },
    [speak, startBackgroundAnalyze],
  );

  // ============ URL upload handler ============
  const onUrlSubmit = useCallback(
    async (url: string) => {
      setUrlDialogOpen(false);
      // Lấy tên file từ URL để readable
      let friendly = "tài liệu từ link";
      try {
        const u = new URL(url);
        const path = u.pathname.split("/").filter(Boolean).pop();
        if (path) friendly = decodeURIComponent(path);
      } catch {}
      await speak(
        `Đang tải tài liệu từ link. ` +
        `Trong lúc đợi, bạn có thể hỏi tôi bất cứ điều gì khác — ` +
        `khi xong tôi sẽ báo bạn ngay.`,
      );
      startBackgroundAnalyze(analyzeUrl(url), friendly);
    },
    [speak, startBackgroundAnalyze],
  );

  const onUrlCancel = useCallback(() => {
    setUrlDialogOpen(false);
    speak("Đã huỷ. Bạn có thể nói lệnh khác.").catch(() => {});
  }, [speak]);

  // ============ Cleanup ============
  useEffect(() => {
    return () => {
      if (ttsAudioRef.current) {
        try { ttsAudioRef.current.pause(); } catch {}
        try { URL.revokeObjectURL(ttsAudioRef.current.src); } catch {}
      }
      if (abortChatRef.current) abortChatRef.current.abort();
    };
  }, []);

  return (
    <>
      {/* Hidden file input — triggered by voice */}
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,image/*"
        className="sr-only"
        aria-hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFilePicked(f);
          // Reset so same file can be picked again
          e.target.value = "";
        }}
      />
      {children({
        state,
        transcript: voiceCommands.transcript,
        interim: voiceCommands.interim,
        lastSpoken,
        isMuted: voiceCommands.isMuted,
        history,
        start: voiceCommands.start,
        stop: voiceCommands.stop,
        triggerFileInput: () => fileInputRef.current?.click(),
        onFilePicked,
        submitText: (text) => {
          const intent = parseVoiceCommand(text);
          if (intent) dispatchIntent(intent, text).catch((e) => console.error(e));
        },
      })}

      {/* URL upload dialog — opened by voice command "tải link" */}
      <UrlInputDialog
        open={urlDialogOpen}
        onOpenChange={setUrlDialogOpen}
        onSubmit={onUrlSubmit}
        onCancel={onUrlCancel}
      />
    </>
  );
}

function typeLabelVi(t: string): string {
  return (
    {
      math: "công thức toán",
      chart: "biểu đồ",
      table: "bảng",
      figure: "hình ảnh",
      text: "văn bản",
    } as Record<string, string>
  )[t] ?? t;
}

