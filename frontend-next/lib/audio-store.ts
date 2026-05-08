"use client";

/**
 * Global audio registry.
 *
 * - Track every <audio> element via register/unregister
 * - Pause all when one starts (single-stream like a podcast app)
 * - Track currently playing source (block_id, label) for context-aware features
 * - Global "stop all" callable from anywhere
 */

import { create } from "zustand";

interface AudioState {
  currentSourceId: string | null;
  currentLabel: string | null;
  currentBlockId: string | null;       // for "Hỏi về phần này"
  registry: Map<string, HTMLAudioElement>;

  register: (id: string, el: HTMLAudioElement, label?: string, blockId?: string) => void;
  unregister: (id: string) => void;
  setCurrent: (id: string | null, label?: string | null, blockId?: string | null) => void;
  pauseAll: () => void;
  pauseOthers: (exceptId: string) => void;
}

export const useAudioStore = create<AudioState>((set, get) => ({
  currentSourceId: null,
  currentLabel: null,
  currentBlockId: null,
  registry: new Map(),

  register: (id, el, label, blockId) => {
    get().registry.set(id, el);
    // Update label/block whenever this audio ele announces (set on play)
    if (label !== undefined) {
      el.dataset.label = label;
    }
    if (blockId !== undefined) {
      el.dataset.blockId = blockId;
    }
  },

  unregister: (id) => {
    const reg = get().registry;
    reg.delete(id);
    if (get().currentSourceId === id) {
      set({ currentSourceId: null, currentLabel: null, currentBlockId: null });
    }
  },

  setCurrent: (id, label = null, blockId = null) =>
    set({ currentSourceId: id, currentLabel: label, currentBlockId: blockId }),

  pauseAll: () => {
    get().registry.forEach((el) => {
      try {
        el.pause();
      } catch {}
    });
    set({ currentSourceId: null, currentLabel: null, currentBlockId: null });
  },

  pauseOthers: (exceptId) => {
    get().registry.forEach((el, id) => {
      if (id !== exceptId) {
        try {
          el.pause();
        } catch {}
      }
    });
  },
}));

/** Convenience: stop everything. Used by Esc handler globally. */
export function stopAllAudio() {
  useAudioStore.getState().pauseAll();
}
