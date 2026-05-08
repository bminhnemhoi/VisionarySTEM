"use client";

import { Ear, Loader2, MicOff, Volume2 } from "lucide-react";

export type VoiceState = "idle" | "listening" | "processing" | "speaking" | "muted";

const STATES: Record<
  VoiceState,
  { label: string; icon: React.ComponentType<{ className?: string }>; bgClass: string; pulse: boolean }
> = {
  idle: { label: "Sẵn sàng", icon: Ear, bgClass: "bg-muted text-muted-foreground", pulse: false },
  listening: { label: "Đang nghe", icon: Ear, bgClass: "bg-success text-success-foreground", pulse: true },
  processing: { label: "Đang nghĩ", icon: Loader2, bgClass: "bg-warning text-warning-foreground", pulse: false },
  speaking: { label: "Đang nói", icon: Volume2, bgClass: "bg-primary text-primary-foreground", pulse: true },
  muted: { label: "Đã tắt mic", icon: MicOff, bgClass: "bg-destructive text-destructive-foreground", pulse: false },
};

interface VoiceIndicatorProps {
  state: VoiceState;
  transcript?: string;
  caption?: string;
  className?: string;
  variant?: "pill" | "banner";
}

/**
 * Voice state indicator — STABLE, no flicker.
 * - Color transitions smoothly via Tailwind transition-colors
 * - Pulsing dot uses Tailwind animate-pulse (no keyframe injection per render)
 * - No exit animation (avoids state-change flash)
 */
export function VoiceIndicator({
  state,
  transcript,
  caption,
  className,
  variant = "pill",
}: VoiceIndicatorProps) {
  const cfg = STATES[state];
  const Icon = cfg.icon;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`flex flex-col items-center gap-2 ${className ?? ""}`}
    >
      <div
        className={`
          inline-flex items-center gap-3 rounded-full font-semibold shadow-md
          transition-colors duration-300
          ${variant === "banner" ? "px-6 py-3 text-base w-full justify-center" : "px-5 py-2.5 text-sm"}
          ${cfg.bgClass}
        `}
      >
        {cfg.pulse && (
          <span className="size-2.5 rounded-full bg-current animate-pulse" aria-hidden />
        )}
        <Icon
          className={`size-5 ${state === "processing" ? "animate-spin" : ""}`}
          aria-hidden
        />
        <span>{caption ? `${caption}: ${cfg.label}` : cfg.label}</span>
      </div>

      {transcript && (
        <p className="max-w-2xl text-sm text-muted-foreground italic" aria-hidden>
          "{transcript}"
        </p>
      )}
    </div>
  );
}
