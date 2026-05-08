"use client";

import { useEffect, useRef, useState, useId } from "react";
import {
  Pause,
  Play,
  Square,
  SkipBack,
  SkipForward,
  Volume2,
  Gauge,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAudioStore } from "@/lib/audio-store";

interface AudioPlayerProps {
  src: string;
  label?: string;
  blockId?: string;          // for context-aware "Hỏi về phần này"
  autoPlay?: boolean;
  className?: string;
  showSpeed?: boolean;        // playback rate selector
  onEnded?: () => void;
}

const SPEED_OPTIONS = [0.75, 1, 1.25, 1.5, 1.75, 2];

/**
 * Accessible audio player with seek, stop, skip ±10s, speed control.
 *
 * - Click anywhere on progress bar = seek
 * - Spacebar (when player has focus) = play/pause
 * - Cooperates with global audio store: only one plays at a time
 * - Esc handled by parent (workspace) via stopAllAudio()
 */
export function AudioPlayer({
  src,
  label,
  blockId,
  autoPlay = false,
  className,
  showSpeed = true,
  onEnded,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const id = useId();
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [seeking, setSeeking] = useState(false);

  const register = useAudioStore((s) => s.register);
  const unregister = useAudioStore((s) => s.unregister);
  const setCurrent = useAudioStore((s) => s.setCurrent);
  const pauseOthers = useAudioStore((s) => s.pauseOthers);

  // Register audio element with global store
  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    register(id, a, label, blockId);
    return () => unregister(id);
  }, [id, label, blockId, register, unregister]);

  // Apply speed to audio element
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed;
  }, [speed]);

  // Auto play on src change
  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (autoPlay) {
      a.play().catch(() => {
        /* browser autoplay block — user must click */
      });
    }
  }, [src, autoPlay]);

  const toggle = () => {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) {
      a.play();
    } else {
      a.pause();
    }
  };

  const stop = () => {
    const a = audioRef.current;
    if (!a) return;
    a.pause();
    a.currentTime = 0;
    setProgress(0);
  };

  const skip = (delta: number) => {
    const a = audioRef.current;
    if (!a) return;
    const newTime = Math.max(0, Math.min(a.duration || 0, a.currentTime + delta));
    a.currentTime = newTime;
    setProgress(newTime);
  };

  const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const a = audioRef.current;
    if (!a) return;
    const newTime = parseFloat(e.target.value);
    a.currentTime = newTime;
    setProgress(newTime);
  };

  // Spacebar toggle when player container has focus (not in inputs)
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === " ") {
      e.preventDefault();
      toggle();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      skip(-5);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      skip(5);
    } else if (e.key === "Escape") {
      stop();
    }
  };

  return (
    <div
      className={`flex items-center gap-2 rounded-xl border bg-muted/30 p-2 ${className ?? ""}`}
      tabIndex={0}
      onKeyDown={onKeyDown}
      role="region"
      aria-label={label ? `Trình phát audio: ${label}` : "Trình phát audio"}
    >
      {/* Play/Pause */}
      <Button
        size="icon"
        variant={playing ? "default" : "outline"}
        onClick={toggle}
        aria-label={playing ? "Tạm dừng (phím cách)" : "Phát (phím cách)"}
        className="rounded-full size-10 shrink-0"
        title={playing ? "Tạm dừng (Space)" : "Phát (Space)"}
      >
        {playing ? <Pause className="size-4" /> : <Play className="size-4 ml-0.5" />}
      </Button>

      {/* Stop (reset to 0) */}
      <Button
        size="icon"
        variant="ghost"
        onClick={stop}
        aria-label="Dừng và quay về đầu (Esc)"
        className="rounded-full size-9 shrink-0 hidden sm:inline-flex"
        title="Dừng (Esc)"
      >
        <Square className="size-3.5" />
      </Button>

      {/* Skip back 10s */}
      <Button
        size="icon"
        variant="ghost"
        onClick={() => skip(-10)}
        aria-label="Tua lui 10 giây (mũi tên trái = 5s)"
        className="rounded-full size-9 shrink-0 relative"
        title="Lui 10s (←)"
      >
        <SkipBack className="size-3.5" />
        <span className="absolute -bottom-0.5 right-0 text-[8px] font-bold leading-none">10</span>
      </Button>

      {/* Skip fwd 10s */}
      <Button
        size="icon"
        variant="ghost"
        onClick={() => skip(10)}
        aria-label="Tua tới 10 giây (mũi tên phải = 5s)"
        className="rounded-full size-9 shrink-0 relative"
        title="Tới 10s (→)"
      >
        <SkipForward className="size-3.5" />
        <span className="absolute -bottom-0.5 right-0 text-[8px] font-bold leading-none">10</span>
      </Button>

      {/* Progress + seek */}
      <div className="flex flex-1 flex-col gap-0.5 min-w-0 px-1">
        {label && (
          <span className="text-[11px] font-medium text-muted-foreground truncate" title={label}>
            {label}
          </span>
        )}
        <input
          type="range"
          min={0}
          max={duration || 1}
          step={0.1}
          value={progress}
          onChange={seek}
          onMouseDown={() => setSeeking(true)}
          onMouseUp={() => setSeeking(false)}
          aria-label="Vị trí phát (kéo để tua)"
          aria-valuenow={Math.floor(progress)}
          aria-valuemax={Math.floor(duration)}
          aria-valuetext={`${formatSeconds(progress)} trên ${formatSeconds(duration)}`}
          className="vs-range w-full h-2 cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-[10px] tabular-nums text-muted-foreground">
          <span aria-hidden>{formatSeconds(progress)}</span>
          <span aria-hidden>-{formatSeconds(Math.max(0, duration - progress))}</span>
        </div>
      </div>

      {/* Speed selector */}
      {showSpeed && (
        <label
          className="hidden md:flex items-center gap-1 text-[11px] cursor-pointer rounded-md border bg-background px-1.5 py-1"
          title="Tốc độ phát"
        >
          <Gauge className="size-3 text-muted-foreground" />
          <select
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            className="bg-transparent outline-none cursor-pointer pr-0.5 font-medium"
            aria-label="Chọn tốc độ phát"
          >
            {SPEED_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
        </label>
      )}

      <Volume2 className="size-3.5 text-muted-foreground shrink-0 hidden sm:inline" aria-hidden />

      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onPlay={() => {
          setPlaying(true);
          pauseOthers(id);
          setCurrent(id, label ?? null, blockId ?? null);
        }}
        onPause={() => {
          setPlaying(false);
        }}
        onTimeUpdate={(e) => {
          if (!seeking) setProgress(e.currentTarget.currentTime);
        }}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onEnded={() => {
          setPlaying(false);
          setProgress(0);
          onEnded?.();
        }}
      />
    </div>
  );
}

function formatSeconds(s: number): string {
  if (!isFinite(s) || isNaN(s)) return "0:00";
  const min = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${min}:${sec.toString().padStart(2, "0")}`;
}
