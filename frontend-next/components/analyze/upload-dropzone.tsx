"use client";

import { Upload, FileText } from "lucide-react";
import { useCallback, useState } from "react";
import { cn, formatBytes } from "@/lib/utils";

interface UploadDropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  currentFile?: File | null;
}

const ACCEPT = "application/pdf,image/png,image/jpeg,image/webp";
const MAX_MB = 20;

export function UploadDropzone({ onFile, disabled, currentFile }: UploadDropzoneProps) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const f = files[0];
      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
      const allowed = ["pdf", "png", "jpg", "jpeg", "webp"];
      if (!allowed.includes(ext)) {
        setError(`Định dạng .${ext} không hỗ trợ. Cần: ${allowed.join(", ")}`);
        return;
      }
      if (f.size > MAX_MB * 1024 * 1024) {
        setError(`File quá lớn. Tối đa ${MAX_MB}MB.`);
        return;
      }
      setError(null);
      onFile(f);
    },
    [onFile],
  );

  return (
    <div className="space-y-2">
      <label
        htmlFor="file-input"
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border bg-muted/30 px-6 py-12 cursor-pointer transition-all",
          "hover:border-primary hover:bg-primary/5",
          drag && "border-primary bg-primary/10 scale-[1.01]",
          disabled && "opacity-50 cursor-not-allowed pointer-events-none",
        )}
      >
        <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          {currentFile ? <FileText className="size-7" /> : <Upload className="size-7" />}
        </div>
        {currentFile ? (
          <div className="text-center">
            <p className="font-semibold text-foreground">{currentFile.name}</p>
            <p className="text-sm text-muted-foreground">
              {formatBytes(currentFile.size)} · sẵn sàng phân tích
            </p>
          </div>
        ) : (
          <>
            <p className="text-base font-semibold text-foreground">
              Kéo thả tệp PDF/ảnh STEM vào đây
            </p>
            <p className="text-sm text-muted-foreground">
              hoặc click để chọn từ máy. Hỗ trợ PDF, PNG, JPG (tối đa {MAX_MB}MB).
            </p>
          </>
        )}
        <input
          id="file-input"
          type="file"
          accept={ACCEPT}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
