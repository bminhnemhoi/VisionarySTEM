"use client";

import { useTheme } from "next-themes";
import { Moon, Sun, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const THEMES = [
  { value: "friendly-light", label: "Sáng", icon: Sun },
  { value: "friendly-dark", label: "Tối", icon: Moon },
  { value: "high-contrast", label: "Tương phản cao", icon: Eye },
] as const;

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-11 w-32" aria-hidden />;

  const current = theme ?? "friendly-light";

  return (
    <div className="flex items-center gap-1 rounded-2xl border bg-card p-1 shadow-sm">
      {THEMES.map(({ value, label, icon: Icon }) => (
        <Tooltip key={value} delayDuration={200}>
          <TooltipTrigger asChild>
            <Button
              variant={current === value ? "default" : "ghost"}
              size="icon"
              onClick={() => setTheme(value)}
              aria-label={`Đổi giao diện sang ${label}`}
              aria-pressed={current === value}
              className="h-9 w-9"
            >
              <Icon className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{label}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
