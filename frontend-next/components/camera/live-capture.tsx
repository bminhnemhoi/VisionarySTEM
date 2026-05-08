"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, Loader2, Pause, Play, RotateCcw, Volume2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AudioPlayer } from "@/components/audio/audio-player";
import { cameraSnapshot, ttsSpeakBlob } from "@/lib/api";

interface Description {
  ts: string;
  spoken_text: string;
  raw_content: string;
  confidence: number;
  has_math?: boolean;
  has_chart?: boolean;
  audio_url?: string;
}

const INTERVAL_OPTIONS = [
  { label: "Mỗi 3 giây", value: 3000 },
  { label: "Mỗi 5 giây", value: 5000 },
  { label: "Mỗi 10 giây", value: 10000 },
  { label: "Thủ công", value: 0 },
];

export function LiveCapture() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [active, setActive] = useState(false);
  const [paused, setPaused] = useState(true);
  const [intervalMs, setIntervalMs] = useState(5000);
  const [analyzing, setAnalyzing] = useState(false);
  const [history, setHistory] = useState<Description[]>([]);
  const [permError, setPermError] = useState<string | null>(null);
  const [snapshotCount, setSnapshotCount] = useState(0);

  // Start camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setActive(true);
      setPermError(null);
      toast.success("Camera đã sẵn sàng");
    } catch (e: any) {
      setPermError(e.message || "Không truy cập được camera");
      toast.error("Cần cấp quyền camera trên trình duyệt");
    }
  };

  const stopCamera = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setActive(false);
    setPaused(true);
  };

  const captureFrame = async (): Promise<Blob | null> => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return null;
    if (video.readyState < 2) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.85);
    });
  };

  const analyzeFrame = async () => {
    if (analyzing) return;
    const blob = await captureFrame();
    if (!blob) return;
    setAnalyzing(true);
    setSnapshotCount((c) => c + 1);

    try {
      const result = await cameraSnapshot(blob);
      let audio_url: string | undefined;
      try {
        const audioBlob = await ttsSpeakBlob(result.spoken_text);
        audio_url = URL.createObjectURL(audioBlob);
      } catch {
        /* TTS optional */
      }

      setHistory((h) => [
        {
          ts: new Date().toLocaleTimeString("vi-VN"),
          spoken_text: result.spoken_text,
          raw_content: result.raw_content,
          confidence: result.confidence,
          has_math: result.has_math,
          has_chart: result.has_chart,
          audio_url,
        },
        ...h.slice(0, 9), // keep last 10
      ]);
    } catch (e: any) {
      toast.error(`Phân tích lỗi: ${e.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  // Auto interval
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (active && !paused && intervalMs > 0) {
      intervalRef.current = setInterval(analyzeFrame, intervalMs);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, paused, intervalMs]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      history.forEach((h) => h.audio_url && URL.revokeObjectURL(h.audio_url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_400px]">
      {/* Video preview */}
      <Card className="overflow-hidden">
        <div className="relative bg-black aspect-video">
          {active ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="size-full object-contain"
              aria-label="Webcam preview"
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-white p-8 text-center">
              <Camera className="size-16 opacity-60" />
              <p className="text-lg font-semibold">Camera chưa bật</p>
              <p className="text-sm opacity-70 max-w-md">
                Bấm "Bật camera" để cấp quyền và bắt đầu phân tích bảng/slide bằng webcam.
              </p>
              {permError && (
                <p className="text-sm text-red-400 max-w-md">⚠️ {permError}</p>
              )}
            </div>
          )}
          {analyzing && (
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-black/60 backdrop-blur px-3 py-1.5 text-white text-sm">
              <Loader2 className="size-3.5 animate-spin" />
              Đang phân tích...
            </div>
          )}
          {active && !paused && intervalMs > 0 && !analyzing && (
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-success/80 backdrop-blur px-3 py-1.5 text-success-foreground text-sm">
              <span className="size-2 rounded-full bg-white animate-pulse" />
              Live · {intervalMs / 1000}s
            </div>
          )}
        </div>
        <canvas ref={canvasRef} className="hidden" />

        <CardContent className="p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {!active ? (
              <Button onClick={startCamera} variant="gradient" size="lg">
                <Camera className="size-4" /> Bật camera
              </Button>
            ) : (
              <>
                <Button
                  onClick={() => setPaused((p) => !p)}
                  variant={paused ? "default" : "outline"}
                >
                  {paused ? <Play className="size-4" /> : <Pause className="size-4" />}
                  {paused ? "Bắt đầu" : "Tạm dừng"}
                </Button>
                <Button onClick={analyzeFrame} variant="secondary" disabled={analyzing}>
                  <Camera className="size-4" /> Chụp ngay
                </Button>
                <Button onClick={stopCamera} variant="outline">
                  <RotateCcw className="size-4" /> Tắt
                </Button>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Tần suất:</span>
            <select
              value={intervalMs}
              onChange={(e) => setIntervalMs(Number(e.target.value))}
              className="text-sm rounded-lg border bg-background px-2 py-1"
            >
              {INTERVAL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <Badge variant="outline">{snapshotCount} ảnh</Badge>
          </div>
        </CardContent>
      </Card>

      {/* History panel */}
      <Card className="flex flex-col">
        <div className="border-b p-4">
          <h2 className="font-bold flex items-center gap-2">
            <Volume2 className="size-4 text-primary" /> Mô tả gần đây
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            10 mô tả mới nhất, kèm audio TTS tự động.
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              Chưa có mô tả. Bật camera để bắt đầu.
            </p>
          ) : (
            history.map((h, i) => (
              <motion.div
                key={`${h.ts}-${i}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="rounded-xl border bg-muted/20 p-3 space-y-2"
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{h.ts}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {Math.round(h.confidence * 100)}%
                  </Badge>
                  {h.has_math && <Badge variant="math" className="text-[10px]">Math</Badge>}
                  {h.has_chart && <Badge variant="chart" className="text-[10px]">Chart</Badge>}
                </div>
                <p className="text-sm leading-relaxed">{h.spoken_text}</p>
                {h.audio_url && <AudioPlayer src={h.audio_url} autoPlay={i === 0} />}
              </motion.div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
