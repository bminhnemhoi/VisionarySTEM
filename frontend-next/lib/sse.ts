/**
 * SSE client for /analyze/stream — uses fetch + ReadableStream because
 * native EventSource doesn't support POST + multipart bodies.
 */

export type SSEEvent = {
  event: string;
  data: any;
};

export async function* streamAnalyze(
  file: File,
): AsyncGenerator<SSEEvent, void, unknown> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/proxy/api/v1/analyze/stream", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.status} ${await response.text()}`);
  }
  if (!response.body) {
    throw new Error("Empty response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";
  let currentData: string[] = [];

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // keep incomplete trailing line

    for (const rawLine of lines) {
      const line = rawLine.replace(/\r$/, "");
      if (line === "") {
        if (currentData.length > 0) {
          const dataStr = currentData.join("\n");
          let parsed: any = dataStr;
          try {
            parsed = JSON.parse(dataStr);
          } catch {
            /* keep as string */
          }
          yield { event: currentEvent, data: parsed };
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

  // Flush trailing event if any
  if (currentData.length > 0) {
    const dataStr = currentData.join("\n");
    let parsed: any = dataStr;
    try {
      parsed = JSON.parse(dataStr);
    } catch {}
    yield { event: currentEvent, data: parsed };
  }
}
