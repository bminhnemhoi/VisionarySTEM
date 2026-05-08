"use client";

/**
 * Browser Web Speech API wrapper — STABLE version.
 *
 * Key fixes for blind UX:
 * - Setup recognition instance ONCE (no callback deps) — avoids re-setup churn
 * - Callback refs instead of effect deps — stable across re-renders
 * - `forceRestart()` exposed — call after TTS finishes to wake mic up
 * - Robust restart with small delay (Chrome needs ~50ms after onend before start can succeed)
 * - Detect Chrome auto-pause during audio playback → restart proactively
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}
interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}
interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((ev: SpeechRecognitionEvent) => void) | null;
  onstart: ((ev: Event) => void) | null;
  onend: ((ev: Event) => void) | null;
  onerror: ((ev: any) => void) | null;
  onspeechstart: ((ev: Event) => void) | null;
  onspeechend: ((ev: Event) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition?: { new (): SpeechRecognitionInstance };
    webkitSpeechRecognition?: { new (): SpeechRecognitionInstance };
  }
}

export interface UseSpeechRecognitionOptions {
  lang?: string;
  continuous?: boolean;
  interimResults?: boolean;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onError?: (err: any) => void;
}

export function useSpeechRecognition(opts: UseSpeechRecognitionOptions = {}) {
  const {
    lang = "vi-VN",
    continuous = true,
    interimResults = true,
  } = opts;

  // Stable callback refs — won't trigger re-setup
  const onTranscriptRef = useRef(opts.onTranscript);
  const onSpeechStartRef = useRef(opts.onSpeechStart);
  const onSpeechEndRef = useRef(opts.onSpeechEnd);
  const onErrorRef = useRef(opts.onError);
  useEffect(() => { onTranscriptRef.current = opts.onTranscript; }, [opts.onTranscript]);
  useEffect(() => { onSpeechStartRef.current = opts.onSpeechStart; }, [opts.onSpeechStart]);
  useEffect(() => { onSpeechEndRef.current = opts.onSpeechEnd; }, [opts.onSpeechEnd]);
  useEffect(() => { onErrorRef.current = opts.onError; }, [opts.onError]);

  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const wantListeningRef = useRef(false);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Synchronous mirror of `listening` state for use in callbacks (state is async)
  const listeningRef = useRef(false);

  // Setup once — NO callback deps
  useEffect(() => {
    if (typeof window === "undefined") return;
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      setSupported(false);
      return;
    }
    setSupported(true);

    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = continuous;
    rec.interimResults = interimResults;
    rec.maxAlternatives = 1;

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let finalText = "";
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        const text = result[0].transcript;
        if (result.isFinal) finalText += text;
        else interimText += text;
      }
      if (finalText) {
        setTranscript((prev) => (prev ? prev + " " : "") + finalText.trim());
        setInterim("");
        onTranscriptRef.current?.(finalText.trim(), true);
      } else if (interimText) {
        setInterim(interimText);
        onTranscriptRef.current?.(interimText, false);
      }
    };

    rec.onstart = () => {
      listeningRef.current = true;
      setListening(true);
    };

    rec.onend = () => {
      listeningRef.current = false;
      setListening(false);
      // Auto-restart with small delay (Chrome needs settling time)
      if (wantListeningRef.current) {
        if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
        restartTimerRef.current = setTimeout(() => {
          try {
            rec.start();
          } catch {
            // Already started or browser blocked — schedule one more retry
            restartTimerRef.current = setTimeout(() => {
              try { rec.start(); } catch {}
            }, 200);
          }
        }, 80);
      }
    };

    rec.onspeechstart = () => onSpeechStartRef.current?.();
    rec.onspeechend = () => onSpeechEndRef.current?.();
    rec.onerror = (err: any) => {
      const code = err?.error;
      // 'no-speech' / 'aborted' are normal — keep listening
      if (code === "no-speech" || code === "aborted") return;
      // 'not-allowed' = permission denied → propagate
      if (code === "not-allowed" || code === "service-not-allowed") {
        wantListeningRef.current = false;
      }
      onErrorRef.current?.(err);
    };

    recognitionRef.current = rec;

    return () => {
      wantListeningRef.current = false;
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      try { rec.abort(); } catch {}
    };
    // Setup once — no deps that change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const start = useCallback(() => {
    if (!recognitionRef.current) return;
    wantListeningRef.current = true;
    try {
      recognitionRef.current.start();
    } catch {
      // Already started — that's fine
    }
  }, []);

  const stop = useCallback(() => {
    if (!recognitionRef.current) return;
    wantListeningRef.current = false;
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    try { recognitionRef.current.stop(); } catch {}
  }, []);

  /**
   * Force-restart recognition. Use after TTS playback completes.
   *
   * KHÔNG tin `listeningRef` — Chrome có thể để recognition trong trạng thái
   * "zombie" sau khi audio playback (listening=true nhưng không fire events thực sự).
   * Pattern duy nhất reliable: stop() → onend tự fire → onend's auto-restart
   * (đã có sẵn lines ~134-148) sẽ start() lại sau 80ms với clean state.
   *
   * Đây cũng chính là pattern mute()/unmute() mà user xác nhận hoạt động.
   */
  const forceRestart = useCallback(() => {
    if (!recognitionRef.current) return;
    wantListeningRef.current = true;
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    try {
      recognitionRef.current.stop();
    } catch {
      // Nếu đã stop (chưa start) hoặc state lỗi → fallback start trực tiếp
      try { recognitionRef.current?.start(); } catch {}
    }
  }, []);

  const reset = useCallback(() => {
    setTranscript("");
    setInterim("");
  }, []);

  return { supported, listening, transcript, interim, start, stop, forceRestart, reset };
}
