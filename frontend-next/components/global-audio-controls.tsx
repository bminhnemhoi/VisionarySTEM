"use client";

import { useEffect } from "react";
import { Square } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAudioStore, stopAllAudio } from "@/lib/audio-store";

/**
 * - Esc anywhere = stop all audio
 * - Floating "Đang phát: ..." pill bottom-right with Stop button
 *   (so user knows what's playing + can stop without scrolling)
 */
export function GlobalAudioControls() {
  const currentLabel = useAudioStore((s) => s.currentLabel);
  const currentSourceId = useAudioStore((s) => s.currentSourceId);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't intercept if typing in inputs
      const target = e.target as HTMLElement;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;

      if (e.key === "Escape") {
        stopAllAudio();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <AnimatePresence>
      {currentSourceId && currentLabel && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-2xl border bg-card shadow-lg px-4 py-2.5"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <span className="recording-dot bg-success" aria-hidden />
          <span className="text-sm">
            <span className="text-muted-foreground">Đang phát: </span>
            <span className="font-medium">{currentLabel}</span>
          </span>
          <button
            onClick={stopAllAudio}
            className="ml-2 rounded-full p-1.5 hover:bg-muted transition-colors"
            aria-label="Dừng tất cả audio (Esc)"
            title="Dừng (Esc)"
          >
            <Square className="size-3.5 fill-current" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
