"use client";

/**
 * useVoiceCommands — orchestrate voice → intent → action for blind students.
 *
 * Combines:
 * - useSpeechRecognition (continuous listening with VAD)
 * - parseVoiceCommand (Vietnamese intent parser)
 * - dispatch action (callback)
 *
 * Auto-submits after silence_auto_send_ms of pause (default 1500ms).
 * Cancels in-flight reply when user starts speaking again (bargein).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { parseVoiceCommand, type VoiceIntent } from "@/lib/voice-command-grammar";
import { useSpeechRecognition } from "@/lib/use-speech-recognition";

export interface VoiceCommandsOptions {
  /** Called when an intent is parsed and ready to dispatch. */
  onIntent: (intent: VoiceIntent, rawText: string) => void | Promise<void>;
  /** Called when user starts speaking — useful for bargein (stop TTS). */
  onSpeechStart?: () => void;
  /** Called when listening starts (mic actually engaged). */
  onListening?: (active: boolean) => void;
  /** Silence duration before auto-submit (ms). Default 1500. */
  silenceMs?: number;
  /** Language code. Default vi-VN. */
  lang?: string;
  /** Auto-start listening on mount? Default false (need user gesture for permission). */
  autoStart?: boolean;
}

export function useVoiceCommands(opts: VoiceCommandsOptions) {
  const { onIntent, onSpeechStart, onListening, silenceMs = 500, lang = "vi-VN", autoStart = false } = opts;

  const [isMuted, setIsMuted] = useState(false);
  // Sync ref mirror cho dùng trong callback (state async). Đảm bảo
  // resumeListening biết được user đã mute để KHÔNG start lại mic.
  const isMutedRef = useRef(false);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const accumulatedRef = useRef<string>("");
  const lastInterimRef = useRef<string>("");

  // SESSION-BASED DEDUPE — robust thay cho timing-based.
  //
  // Mỗi câu user nói = 1 utterance session. Khi user bắt đầu nói (`onspeechstart`),
  // bump session id + reset `dispatched`. Sau khi `onIntent` fire → `dispatched = true`,
  // chặn MỌI transcript tiếp theo (interim hay final, dù browser re-emit) cho đến khi
  // user nói câu MỚI. Điều này khắc phục:
  //  - Final result đến SAU khi interim đã dispatch (12s sau, vượt window)
  //  - Web Speech `abort()` không clear buffer → restart re-emit transcript cũ
  //  - Bất kỳ race condition nào khác
  const sessionRef = useRef<{ id: number; dispatched: boolean }>({ id: 0, dispatched: false });

  const handleTranscript = useCallback(
    (text: string, isFinal: boolean) => {
      // Đã dispatch cho session này rồi → skip mọi thứ cho đến khi user nói câu mới
      if (sessionRef.current.dispatched) return;

      // Reset silence timer on every new transcript chunk (interim or final)
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

      if (isFinal) {
        accumulatedRef.current = (accumulatedRef.current + " " + text).trim();
        lastInterimRef.current = "";
      } else {
        // Track latest interim — used as fallback if recognition never finalizes
        lastInterimRef.current = text.trim();
      }

      // Schedule auto-submit when user pauses speaking
      silenceTimerRef.current = setTimeout(() => {
        // Re-check dispatched flag (có thể đã set giữa lúc đợi)
        if (sessionRef.current.dispatched) return;

        // Prefer accumulated final text; if empty, fall back to interim
        // (Chrome vi-VN sometimes never sends final results for short utterances)
        const fullText = accumulatedRef.current || lastInterimRef.current;
        if (!fullText || fullText.length < 2) return;

        // Khoá session NGAY để tránh race với final result đến sau
        sessionRef.current.dispatched = true;
        accumulatedRef.current = "";
        lastInterimRef.current = "";

        const intent = parseVoiceCommand(fullText);
        if (intent) {
          Promise.resolve(onIntent(intent, fullText)).catch((e) =>
            console.error("[voice-commands] onIntent error:", e),
          );
        }
      }, silenceMs);
    },
    [onIntent, silenceMs],
  );

  const handleSpeechStart = useCallback(() => {
    // User bắt đầu nói câu MỚI → bump session, reset dispatched
    sessionRef.current = { id: sessionRef.current.id + 1, dispatched: false };
    // Clear any stale buffered text from previous session
    accumulatedRef.current = "";
    lastInterimRef.current = "";
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    onSpeechStart?.();
  }, [onSpeechStart]);

  const { supported, listening, transcript, interim, start, stop, forceRestart, reset } = useSpeechRecognition({
    lang,
    continuous: true,
    interimResults: true,
    onTranscript: handleTranscript,
    onSpeechStart: handleSpeechStart,
  });

  // Notify parent of listening state changes
  useEffect(() => {
    onListening?.(listening);
  }, [listening, onListening]);

  // Auto-start (only if requested AND not muted)
  useEffect(() => {
    if (autoStart && !isMuted && supported) {
      start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart, supported]);

  const mute = useCallback(() => {
    isMutedRef.current = true;
    setIsMuted(true);
    stop();
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    accumulatedRef.current = "";
    lastInterimRef.current = "";
    sessionRef.current = { id: sessionRef.current.id + 1, dispatched: true };
    reset();
  }, [stop, reset]);

  const unmute = useCallback(() => {
    isMutedRef.current = false;
    setIsMuted(false);
    start();
  }, [start]);

  /**
   * Pause/resume mic CHO INTERNAL USE — KHÔNG đổi `isMuted` UI state.
   * Dùng để pause mic trong khi TTS đang phát → tránh AI's own voice
   * leak vào mic → tránh self-dispatch loop.
   *
   * QUAN TRỌNG về `dispatched=true`:
   *   `recognition.stop()` flush FINAL onresult event ngay trước onend.
   *   Nếu `dispatched=false`, handleTranscript sẽ process final đó →
   *   schedule silence timer → fire dispatch lần 2 sau khi mic resume.
   *   Đặt `dispatched=true` trong cả pause + resume để BLOCK mọi onresult
   *   trong giai đoạn AI speak. Chỉ `handleSpeechStart` từ user thực
   *   sự cất tiếng (sau resume) mới reset `dispatched=false` để dispatch.
   */
  const pauseListening = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    accumulatedRef.current = "";
    lastInterimRef.current = "";
    // Bump id + LOCK dispatched (block any final result emitted by stop())
    sessionRef.current = { id: sessionRef.current.id + 1, dispatched: true };
    stop();
  }, [stop]);

  const resumeListening = useCallback(() => {
    // QUAN TRỌNG: nếu user đã chủ động mute → KHÔNG resume mic.
    // pauseListening/resumeListening là cycle nội bộ cho TTS speak.
    // mute là user-facing intent (tắt mic) — phải tôn trọng.
    if (isMutedRef.current) return;
    // Vẫn LOCK dispatched=true — chờ user's real onspeechstart unlock.
    sessionRef.current = { id: sessionRef.current.id + 1, dispatched: true };
    start();
  }, [start]);

  return {
    supported,
    listening,
    isMuted,
    transcript,
    interim,
    start: unmute,
    stop: mute,
    mute,
    unmute,
    pauseListening,
    resumeListening,
    /** Force-restart recognition. Call after TTS completes (Chrome auto-pauses mic during audio). */
    forceRestart,
    reset,
  };
}
