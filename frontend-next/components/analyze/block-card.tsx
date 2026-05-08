"use client";

import { motion } from "framer-motion";
import { AlertTriangle, MapPin, MessageCircleQuestion, Music2, Volume2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ContentBlock, ttsBlockUrl, sonifyBlockUrl } from "@/lib/api";
import { useState } from "react";
import { AudioPlayer } from "@/components/audio/audio-player";

interface BlockCardProps {
  block: ContentBlock;
  documentId: string;
  rate: string;
  pitch: string;
  index: number;
  onAskAbout?: (block: ContentBlock) => void;
}

const REGION_LABELS: Record<string, string> = {
  "top-left": "Trên trái",
  "top-center": "Trên giữa",
  "top-right": "Trên phải",
  "center-left": "Giữa trái",
  center: "Trung tâm",
  "center-right": "Giữa phải",
  "bottom-left": "Dưới trái",
  "bottom-center": "Dưới giữa",
  "bottom-right": "Dưới phải",
};

const TYPE_LABELS: Record<string, string> = {
  text: "Văn bản",
  math: "Công thức",
  chart: "Biểu đồ",
  table: "Bảng",
  figure: "Hình",
};

export function BlockCard({ block, documentId, rate, pitch, index, onAskAbout }: BlockCardProps) {
  const [audioMode, setAudioMode] = useState<"none" | "tts" | "sonify">("none");

  const ttsUrl = ttsBlockUrl(block.id, documentId, rate, pitch);
  const sonifyUrl = sonifyBlockUrl(block.id, documentId);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      <Card className="card-hoverable">
        <div className="p-5">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={block.type as any}>{TYPE_LABELS[block.type] ?? block.type}</Badge>
              <span className="text-xs font-mono text-muted-foreground">{block.id}</span>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="size-3" />
                {REGION_LABELS[block.coordinates.region] ?? block.coordinates.region}
              </span>
              <span className="text-xs text-muted-foreground">
                · trang {block.coordinates.page}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {block.needs_review && (
                <Badge variant="warning" className="gap-1" title={block.critique_issues?.join("; ")}>
                  <AlertTriangle className="size-3" />
                  Cần xem lại
                </Badge>
              )}
              <Badge variant="outline">
                {Math.round((block.confidence ?? 0) * 100)}%
              </Badge>
            </div>
          </div>

          {block.latex && (
            <div className="my-3 rounded-xl bg-muted/40 border border-border/60 p-3 font-mono text-sm break-all">
              {block.latex}
            </div>
          )}

          <p className="text-base leading-relaxed">
            <Volume2 className="inline size-4 text-primary mr-1.5 align-text-bottom" aria-hidden />
            <span className="italic text-foreground/90">{block.spoken_text}</span>
          </p>

          {block.alt_text_long && (
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                Mô tả chi tiết
              </summary>
              <p className="mt-2 text-muted-foreground leading-relaxed">{block.alt_text_long}</p>
            </details>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={audioMode === "tts" ? "default" : "outline"}
              onClick={() => setAudioMode(audioMode === "tts" ? "none" : "tts")}
            >
              <Volume2 className="size-3.5" />
              {audioMode === "tts" ? "Đang phát" : "Nghe"}
            </Button>

            {block.type === "chart" && (
              <Button
                size="sm"
                variant={audioMode === "sonify" ? "success" : "outline"}
                onClick={() => setAudioMode(audioMode === "sonify" ? "none" : "sonify")}
                title="Sonification — chuyển biểu đồ thành chuỗi pitch âm thanh"
              >
                <Music2 className="size-3.5" />
                {audioMode === "sonify" ? "Đang sonify" : "Nghe biểu đồ"}
              </Button>
            )}

            {onAskAbout && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onAskAbout(block)}
                title="Hỏi gia sư AI về phần này"
                className="ml-auto"
              >
                <MessageCircleQuestion className="size-3.5" />
                Hỏi về phần này
              </Button>
            )}
          </div>

          {audioMode === "tts" && (
            <AudioPlayer
              src={ttsUrl}
              autoPlay
              className="mt-3"
              label={`${TYPE_LABELS[block.type] ?? block.type} — ${block.id}`}
              blockId={block.id}
              onEnded={() => setAudioMode("none")}
            />
          )}
          {audioMode === "sonify" && (
            <AudioPlayer
              src={sonifyUrl}
              autoPlay
              className="mt-3"
              label={`Sonification — ${block.id}`}
              blockId={block.id}
              onEnded={() => setAudioMode("none")}
            />
          )}

          {block.critique_issues && block.critique_issues.length > 0 && (
            <details className="mt-3 text-sm rounded-lg bg-warning/10 border border-warning/30 p-3">
              <summary className="cursor-pointer flex items-center gap-2 text-warning-foreground/90 font-medium">
                <AlertTriangle className="size-4" />
                {block.critique_issues.length} vấn đề được cảnh báo
              </summary>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-muted-foreground">
                {block.critique_issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
