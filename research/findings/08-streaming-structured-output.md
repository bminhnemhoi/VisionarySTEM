# Gemini Streaming + Structured Output

## API hiện hành (google-genai SDK 2026)
- `client.models.generate_content_stream(...)` — streaming chunks
- `response_mime_type="application/json"` + `response_schema=PydanticModel` cho structured output
- Schema preserves property ordering, supports `anyOf`, `$ref`

## Vấn đề khi kết hợp streaming + JSON schema
JSON streaming là tricky vì JSON valid chỉ ở cuối. SDK trả từng chunk nhưng JSON dở dang **không parse được** bằng `json.loads`.

## Giải pháp đề xuất

### Phương án A: Streaming raw text, parse theo block boundary
Yêu cầu Gemini emit JSON theo dòng (NDJSON-like) hoặc separator pattern:
```python
prompt = """
Trả về mỗi block trên một dòng riêng kết thúc bằng '<<END>>'.
Format: {"id": ..., "type": ..., "spoken_text": ...}
<<END>>
"""

async for chunk in client.models.generate_content_stream(...):
    buffer += chunk.text
    while "<<END>>" in buffer:
        line, _, buffer = buffer.partition("<<END>>")
        try:
            block = json.loads(line)
            yield block  # SSE event
        except: pass
```

### Phương án B: Partial JSON parser
Dùng library như **`json-stream`** hoặc **`partial-json-parser`** parse JSON dở dang → emit khi 1 phần tử mảng `content_blocks` complete.

```python
from partial_json_parser import loads, Allow
async for chunk in stream:
    buffer += chunk.text
    parsed = loads(buffer, allow_partial=Allow.ALL)
    new_blocks = parsed.get("content_blocks", [])[len(emitted):]
    for b in new_blocks:
        if "spoken_text" in b:  # đảm bảo block đầy đủ
            yield b
            emitted.append(b)
```

### Phương án C: Hybrid — sequential page-level streaming
- PDF nhiều trang → start `asyncio.gather` cho mỗi trang
- Trang nào xong trước → push event ngay
- Đơn giản nhất, không cần partial JSON parser
- **Khuyến nghị cho MVP**

## Thực thi cho VisionarySTEM
```python
@app.post("/api/v1/analyze/stream")
async def analyze_stream(file: UploadFile = File(...)):
    async def event_generator():
        # 1. Save & detect pages
        yield sse_event("status", {"phase": "uploaded", "pages": n})
        
        # 2. Parallel analyze pages (Phương án C)
        tasks = [analyze_page_async(p) for p in pages]
        for completed in asyncio.as_completed(tasks):
            page_result = await completed
            for block in page_result.content_blocks:
                yield sse_event("block", block.model_dump())
        
        yield sse_event("done", {})
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Mục tiêu performance
- Time-to-first-block (TTFB): ≤ 1s
- Time-to-full-page: ≤ 5s/trang (so với 19s hiện tại)
- Parallel speedup cho multi-page: ~3-4x

## Sources
- [Gemini Structured Output docs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Google announces JSON Schema support](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/)
- [Instructor genai integration](https://python.useinstructor.com/integrations/genai/)
- [Vertex AI Structured Output](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output)
