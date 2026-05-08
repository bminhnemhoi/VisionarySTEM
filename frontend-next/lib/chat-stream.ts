/**
 * Stream tutor chat replies via SSE.
 * Yields { event, data } tuples — same shape as lib/sse.ts but for chat.
 */

export type ChatStreamEvent =
  | { event: "token"; data: { text: string; accumulated: string } }
  | { event: "done"; data: { reply_text: string; cited_blocks: string[]; session_id: string } }
  | { event: "error"; data: { detail: string } };

export interface StreamChatPayload {
  document_id: string;
  session_id: string;
  message: string;
  focus_block_id?: string;
}

export async function* streamChat(
  payload: StreamChatPayload,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent, void, unknown> {
  const response = await fetch("/api/proxy/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed: ${response.status} ${await response.text()}`);
  }
  if (!response.body) {
    throw new Error("Empty response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";
  let currentData: string[] = [];

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, "");
        if (line === "") {
          if (currentData.length > 0) {
            const dataStr = currentData.join("\n");
            let parsed: any = dataStr;
            try {
              parsed = JSON.parse(dataStr);
            } catch {}
            yield { event: currentEvent as any, data: parsed };
          }
          currentEvent = "message";
          currentData = [];
        } else if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          currentData.push(line.slice(5).replace(/^ /, ""));
        }
      }
    }
  } finally {
    try {
      reader.cancel();
    } catch {}
  }
}
