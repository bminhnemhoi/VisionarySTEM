"use client";

import { Download, BookOpen, Braces, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { epub3DownloadUrl, brailleDocumentUrl } from "@/lib/api";

interface ExportPanelProps {
  documentId: string;
  filename?: string;
}

export function ExportPanel({ documentId, filename }: ExportPanelProps) {
  const baseName = (filename ?? "document").replace(/\.[^.]+$/, "");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Download className="size-4" />
          Xuất tài liệu
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button variant="outline" className="w-full justify-start" asChild>
          <a
            href={epub3DownloadUrl(documentId)}
            download={`${baseName}.epub`}
            aria-label="Tải file EPUB3 với MathML"
          >
            <BookOpen className="size-4 text-block-figure" />
            <span className="flex-1 text-left">EPUB3 + MathML</span>
            <Badge variant="outline" className="text-[10px]">.epub</Badge>
          </a>
        </Button>

        <Button variant="outline" className="w-full justify-start" asChild>
          <a
            href={brailleDocumentUrl(documentId)}
            download={`${baseName}.braille.txt`}
            aria-label="Tải file Unicode Braille"
          >
            <Braces className="size-4 text-block-text" />
            <span className="flex-1 text-left">Unicode Braille</span>
            <Badge variant="outline" className="text-[10px]">.txt</Badge>
          </a>
        </Button>

        <Button variant="ghost" className="w-full justify-start text-xs" disabled>
          <FileText className="size-4 text-muted-foreground" />
          <span className="flex-1 text-left">DAISY 3.0 audio book (sắp ra mắt)</span>
        </Button>

        <p className="text-[11px] text-muted-foreground pt-2 border-t mt-3">
          💡 EPUB3 mở được trên Thorium Reader, iBooks, Calibre. Braille hiển thị
          Unicode (U+2800-U+28FF) hoặc kết nối Braille display qua bluetooth.
        </p>
      </CardContent>
    </Card>
  );
}
