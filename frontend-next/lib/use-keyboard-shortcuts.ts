"use client";

import { useEffect } from "react";

export type Shortcut = {
  key: string;            // e.g. "?", "Space", "ArrowRight"
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;    // Vietnamese description shown in help dialog
  action: () => void;
  preventDefault?: boolean;
  /** Skip if focus is in input/textarea/contenteditable. */
  skipInInputs?: boolean;
};

function inEditableElement(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName?.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (el.isContentEditable) return true;
  return false;
}

/**
 * Register global keyboard shortcuts. Returns nothing.
 *
 * Usage:
 *   useKeyboardShortcuts([
 *     { key: " ", description: "Phát/tạm dừng", action: togglePlay, preventDefault: true },
 *   ]);
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[], enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const handler = (e: KeyboardEvent) => {
      for (const sc of shortcuts) {
        const keyMatch =
          e.key === sc.key ||
          (sc.key === "Space" && e.key === " ") ||
          e.code === sc.key;
        if (!keyMatch) continue;
        if (sc.ctrl !== undefined && e.ctrlKey !== sc.ctrl) continue;
        if (sc.shift !== undefined && e.shiftKey !== sc.shift) continue;
        if (sc.alt !== undefined && e.altKey !== sc.alt) continue;
        if (sc.meta !== undefined && e.metaKey !== sc.meta) continue;

        if (sc.skipInInputs && inEditableElement(e.target)) continue;

        if (sc.preventDefault) e.preventDefault();
        sc.action();
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [shortcuts, enabled]);
}

/**
 * Format a shortcut as a string for display: "Ctrl+Shift+K"
 */
export function formatShortcut(sc: Pick<Shortcut, "key" | "ctrl" | "shift" | "alt" | "meta">): string {
  const parts: string[] = [];
  if (sc.ctrl) parts.push("Ctrl");
  if (sc.shift) parts.push("Shift");
  if (sc.alt) parts.push("Alt");
  if (sc.meta) parts.push("⌘");
  parts.push(sc.key === " " ? "Space" : sc.key);
  return parts.join("+");
}
