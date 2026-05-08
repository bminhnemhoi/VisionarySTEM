#!/usr/bin/env python3
"""
VisionarySTEM self-test — automation cho phần backend + logic.
Phần voice/mic/UI không test được tự động (cần browser + human).
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Force UTF-8 stdout for Vietnamese chars on Windows (default cp1252 chokes)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "http://127.0.0.1:8000/api/v1"
FE = "http://127.0.0.1:3000"
ROOT = Path(__file__).resolve().parent.parent

PASS = 0
FAIL = 0
FAIL_DETAILS: list[str] = []


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"[PASS] {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    FAIL_DETAILS.append(msg)
    print(f"[FAIL] {msg}")


def http_get(url: str, timeout: float = 10) -> tuple[int, bytes]:
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except URLError as e:
        return 0, str(e).encode()


def http_post_json(url: str, body: dict, timeout: float = 30) -> tuple[int, bytes]:
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except URLError as e:
        return 0, str(e).encode()


def http_post_query(url: str, params: dict, timeout: float = 30) -> tuple[int, bytes]:
    full = url + "?" + urlencode(params)
    req = Request(full, data=b"", method="POST")
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except URLError as e:
        return 0, str(e).encode()


def section(title: str) -> None:
    print()
    print(f"=== {title} ===")


def main() -> int:
    print("=" * 70)
    print("VisionarySTEM SELF-TEST — Backend + Logic")
    print("=" * 70)

    # ============ A. Servers up ============
    section("A. Servers")
    code, body = http_get(f"{API}/health", timeout=3)
    if code == 200:
        ok("A1 Backend /health responds")
        h = json.loads(body)
        if h.get("version") == "2.1.0":
            ok("A2 Backend version 2.1.0")
        else:
            fail(f"A2 version: {h.get('version')}")
        if h.get("gemini_model") == "gemini-2.5-flash":
            ok("A3 Gemini model gemini-2.5-flash")
        else:
            fail(f"A3 model: {h.get('gemini_model')}")
    else:
        fail(f"A1 Backend not 200: code={code}")

    code, _ = http_get(f"{FE}/", timeout=3)
    if code == 200:
        ok("A4 Frontend responds 200")
    else:
        fail(f"A4 Frontend code={code}")

    # ============ B. Mock data ============
    section("B. Mock data")
    code, body = http_get(f"{API}/mock/analyze", timeout=30)
    if code != 200:
        fail(f"B0 mock endpoint code={code}")
    else:
        m = json.loads(body)
        blocks = m.get("content_blocks", [])
        meta = m.get("document_metadata", {})

        if len(blocks) == 13:
            ok("B1 Mock has 13 blocks")
        else:
            fail(f"B1 expected 13 blocks, got {len(blocks)}")

        if meta.get("total_pages") == 2:
            ok("B2 Mock has 2 pages")
        else:
            fail(f"B2 pages: {meta.get('total_pages')}")

        if meta.get("filename") == "vat_ly_10_chuong_2_dinh_luat_newton.pdf":
            ok("B3 Mock filename")
        else:
            fail(f"B3 filename: {meta.get('filename')}")

        types = {b["type"] for b in blocks}
        for t in ["text", "math", "table", "chart", "figure"]:
            if t in types:
                ok(f"B4-{t} type present")
            else:
                fail(f"B4-{t} missing")

        # Spatial index covers all blocks
        all_ids = {b["id"] for b in blocks}
        mapped = set()
        for region_ids in m.get("spatial_index", {}).get("regions", {}).values():
            mapped.update(region_ids)
        if all_ids == mapped:
            ok("B5 spatial_index covers all blocks")
        else:
            fail(f"B5 missing: {all_ids - mapped}, extra: {mapped - all_ids}")

    # ============ C. Library ============
    section("C. Library (6 samples)")
    code, body = http_get(f"{API}/library", timeout=5)
    if code != 200:
        fail(f"C0 library code={code}")
    else:
        lib = json.loads(body)
        if lib.get("count") == 6:
            ok("C1 Library count 6")
        else:
            fail(f"C1 count: {lib.get('count')}")

        slugs_in_resp = {item["slug"] for item in lib.get("items", [])}
        for slug in ["physics", "calculus", "linear_algebra", "chemistry", "statistics", "wave_physics"]:
            if slug in slugs_in_resp:
                ok(f"C2-{slug} slug present")
            else:
                fail(f"C2-{slug} slug missing")

    # PDF files exist
    samples_dir = ROOT / "tests" / "sample_data"
    for f in [
        "sample_physics.pdf", "sample_calculus.pdf", "sample_linear_algebra.pdf",
        "sample_chemistry.pdf", "sample_statistics.pdf", "sample_wave_physics.pdf",
    ]:
        if (samples_dir / f).exists():
            ok(f"C3-{f} exists")
        else:
            fail(f"C3-{f} missing")

    # ============ D. TTS ============
    section("D. TTS Aoede")
    code, body = http_post_query(
        f"{API}/tts/v2/speak",
        {"text": "Test giọng tiếng Việt", "voice": "Aoede", "mood": "warm"},
        timeout=30,
    )
    if code == 200:
        ok("D1 TTS responds 200")
        if len(body) > 1000:
            ok(f"D2 WAV size {len(body)} bytes")
        else:
            fail(f"D2 too small: {len(body)}")
        # Accept WAV (Gemini Aoede primary) OR MP3 (Edge TTS fallback when Gemini quota/fail)
        if body[:4] == b"RIFF":
            ok("D3 WAV header valid (RIFF) — Gemini Aoede")
        elif body[:3] == b"ID3" or body[:2] == b"\xff\xfb" or body[:2] == b"\xff\xf3":
            ok("D3 MP3 header valid — Edge TTS fallback (Gemini quota/error)")
        else:
            fail(f"D3 unknown audio format: header={body[:4]!r}")
    else:
        fail(f"D1 TTS code={code}")

    # ============ E. /assist ============
    section("E. /assist (general Q&A, no doc)")
    code, body = http_post_json(
        f"{API}/assist", {"question": "Niu-ton la ai?"}, timeout=30,
    )
    if code == 200:
        r = json.loads(body)
        reply = r.get("reply_text", "")
        if len(reply) > 100:
            ok(f"E1 reply length {len(reply)} >100 chars")
        else:
            fail(f"E1 reply too short: {len(reply)}")
        # Check no English math
        if re.search(r"\bequals\b|\bplus\b|\bminus\b", reply, re.I):
            fail("E2 Contains English math word (BAD)")
        else:
            ok("E2 No English math reading")
    else:
        fail(f"E0 /assist code={code}, body={body[:200]!r}")

    # ============ F. /chat ============
    section("F. /chat (tutor with mock doc)")
    # Mock doc must be registered first — already done by /mock/analyze in B
    code, body = http_post_json(
        f"{API}/chat",
        {
            "document_id": "mock_doc",
            "session_id": "selftest_chat_1",
            "message": "Ban co the lam duoc gi voi tai lieu nay?",
            "voice_mode": False,
        },
        timeout=60,
    )
    if code == 200:
        r = json.loads(body)
        reply = r.get("reply_text", "")
        if len(reply) > 200:
            ok(f"F1 /chat reply length {len(reply)} >200 chars")
        else:
            fail(f"F1 reply too short: {len(reply)}")

        # CRITICAL: no block_xxx in reply text (user complained about this)
        block_ids = re.findall(r"block_\d+", reply)
        if not block_ids:
            ok("F2 No 'block_xxx' in reply text")
        else:
            fail(f"F2 Reply contains block IDs: {block_ids}")

        # Cited blocks tracked internally
        cited = r.get("cited_blocks", [])
        if cited:
            ok(f"F3 cited_blocks tracked internally ({len(cited)} items)")
        else:
            fail("F3 no cited_blocks")

        followups = r.get("suggested_followups", [])
        if followups:
            ok(f"F4 Has {len(followups)} suggested followups")
        else:
            fail("F4 no followups")

        # Reply uses natural language cues
        natural_cues = ["phần", "công thức", "ví dụ", "định luật", "biểu đồ", "bài tập"]
        if any(c in reply.lower() for c in natural_cues):
            ok("F5 Reply uses natural cues (phần/công thức/etc.)")
        else:
            fail(f"F5 No natural cues in reply: {reply[:200]}")

        # Reply doesn't use markdown bullets
        if re.search(r"^\s*[\*\-]\s+", reply, re.M):
            fail("F6 Reply contains markdown bullets (BAD for TTS)")
        else:
            ok("F6 No markdown bullets")
    else:
        fail(f"F0 /chat code={code}, body={body[:200]!r}")

    # ============ G. /analyze-url validation ============
    section("G. /analyze-url validation")
    code, _ = http_post_json(
        f"{API}/analyze-url", {"url": "ftp://example.com/x.pdf"}, timeout=10,
    )
    if code == 400:
        ok("G1 ftp:// rejected (400)")
    else:
        fail(f"G1 ftp:// got {code}")

    code, _ = http_post_json(
        f"{API}/analyze-url", {"url": ""}, timeout=10,
    )
    if code == 400:
        ok("G2 Empty URL rejected")
    else:
        fail(f"G2 empty URL got {code}")

    # G3: HTML article — uses NEW trafilatura branch (httpbin returns Moby-Dick excerpt)
    start = time.time()
    code, body = http_post_json(
        f"{API}/analyze-url", {"url": "https://httpbin.org/html"}, timeout=120,
    )
    elapsed = time.time() - start
    if code == 200:
        r = json.loads(body)
        n = len(r.get("content_blocks", []))
        if n > 0:
            ok(f"G3 HTML article → {n} blocks ({elapsed:.1f}s, NEW branch)")
        else:
            fail("G3 HTML article: no blocks")
    else:
        fail(f"G3 HTML article: code={code}")

    # G4: HTML page too short → friendly reject
    code, body = http_post_json(
        f"{API}/analyze-url", {"url": "https://example.com"}, timeout=30,
    )
    if code == 400:
        try:
            detail = json.loads(body).get("detail", "")
        except Exception:
            detail = ""
        if "không lấy được nội dung" in detail.lower() or "không có nội dung" in detail.lower():
            ok("G4 Short HTML page → friendly Vietnamese error")
        else:
            fail(f"G4 Short HTML: detail not friendly: {detail[:100]}")
    else:
        fail(f"G4 Short HTML: code={code}")

    # ============ H. Library load ============
    section("H. Library load — physics (real Gemini analyze)")
    start = time.time()
    code, body = http_post_query(f"{API}/library/physics/analyze", {}, timeout=60)
    elapsed = time.time() - start
    if code == 200:
        r = json.loads(body)
        n = len(r.get("content_blocks", []))
        if n > 0:
            ok(f"H1 Library physics → {n} blocks ({elapsed:.1f}s)")
        else:
            fail("H1 no blocks returned")
    else:
        fail(f"H1 code={code}")

    # ============ I. /chat/stream (SSE) ============
    section("I. /chat/stream (SSE)")
    # Use raw urllib for SSE — read line-by-line
    req = Request(
        f"{API}/chat/stream",
        data=json.dumps({
            "document_id": "mock_doc",
            "session_id": "selftest_stream",
            "message": "tom tat ngan gon",
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        events_seen: list[str] = []
        with urlopen(req, timeout=60) as r:
            for raw in r:
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("event:"):
                    events_seen.append(line.split(":", 1)[1].strip())
                if "done" in events_seen:
                    break
        if "token" in events_seen:
            ok("I1 SSE token events received")
        else:
            fail(f"I1 no token events; saw: {events_seen[:5]}")
        if "done" in events_seen:
            ok("I2 SSE done event received")
        else:
            fail(f"I2 no done event; saw: {events_seen[:5]}")
    except Exception as e:
        fail(f"I0 SSE exception: {e}")

    # ============ O. Hidden gems (EPUB3 + Braille + Sonification) ============
    section("O. Hidden gems showcase")
    # Trigger mock to register doc
    http_get(f"{API}/mock/analyze", timeout=30)

    # O1: EPUB3 export
    code, body = http_get(f"{API}/export/epub3/mock_doc", timeout=30)
    if code == 200 and body[:4] == b"PK\x03\x04":
        ok(f"O1 EPUB3 export valid ZIP ({len(body)} bytes)")
    else:
        fail(f"O1 EPUB3 code={code} magic={body[:4]!r}")

    # O2: Braille export
    code, body = http_get(f"{API}/export/braille/mock_doc", timeout=30)
    if code == 200:
        # Check has Unicode Braille chars (U+2800 - U+28FF)
        has_braille = any("⠀" <= c <= "⣿" for c in body.decode("utf-8", errors="replace")[:5000])
        if has_braille:
            ok(f"O2 Braille export valid ({len(body)} bytes, has ⠿ chars)")
        else:
            fail("O2 Braille no actual braille chars")
    else:
        fail(f"O2 Braille code={code}")

    # O3: Sonify chart block_007 (mock data has chart at block_007)
    code, body = http_get(
        f"{API}/sonify/block_007?document_id=mock_doc", timeout=30,
    )
    if code == 200 and body[:4] == b"RIFF":
        ok(f"O3 Sonify WAV valid ({len(body)} bytes)")
    else:
        fail(f"O3 Sonify code={code} magic={body[:4]!r}")

    # ============ M. Web search agent (Phase 2) ============
    section("M. Web search agent — Gemini grounding")
    start = time.time()
    code, body = http_post_json(
        f"{API}/agent/search",
        {"query": "định luật ba Newton", "max_sources": 5},
        timeout=60,
    )
    elapsed = time.time() - start
    if code == 200:
        r = json.loads(body)
        summary = r.get("summary", "")
        sources = r.get("sources", [])
        if len(summary) > 100:
            ok(f"M1 Web search summary {len(summary)} chars ({elapsed:.1f}s)")
        else:
            fail(f"M1 summary too short: {len(summary)}")
        if len(sources) > 0:
            ok(f"M2 Web search returned {len(sources)} sources")
        else:
            fail("M2 no sources returned")
        # Verify Vietnamese reply (no English math)
        if re.search(r"\bequals\b|\bplus\b|\bminus\b", summary, re.I):
            fail("M3 Summary contains English math (BAD)")
        else:
            ok("M3 Summary in Vietnamese (no English math)")
    else:
        fail(f"M0 /agent/search code={code}")

    # M4: Empty query validation
    code, _ = http_post_json(
        f"{API}/agent/search", {"query": "", "max_sources": 5}, timeout=10,
    )
    if code in (400, 422):
        ok(f"M4 Empty query rejected ({code})")
    else:
        fail(f"M4 empty query got {code}")

    # ============ N. Multi-step agent /agent/run (Phase 3) ============
    section("N. Multi-step agent — planner + executor SSE")
    try:
        req = Request(
            f"{API}/agent/run",
            data=json.dumps({
                "request": "tìm bài tập chất béo và bài tập định luật Newton",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        events_seen: list[str] = []
        steps_executed = 0
        with urlopen(req, timeout=180) as r:
            for raw in r:
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("event:"):
                    ev = line.split(":", 1)[1].strip()
                    events_seen.append(ev)
                    if ev == "step_done":
                        steps_executed += 1
                if "plan_done" in events_seen:
                    break
        if "plan_ready" in events_seen:
            ok("N1 plan_ready event received")
        else:
            fail(f"N1 no plan_ready; saw: {events_seen[:5]}")
        if steps_executed > 0:
            ok(f"N2 {steps_executed} steps executed")
        else:
            fail("N2 no steps executed")
        if "plan_done" in events_seen:
            ok("N3 plan_done event received")
        else:
            fail("N3 no plan_done")
    except Exception as e:
        fail(f"N0 /agent/run exception: {e}")

    # ============ J. Voice grammar (frontend) ============
    section("J. Voice grammar (run via tsx)")
    test_grammar = ROOT / "frontend-next" / "test_grammar_selftest.ts"
    test_grammar.write_text(
        """
import { parseVoiceCommand } from "./lib/voice-command-grammar";
const cases: Array<[string, string]> = [
  ["tài liệu mẫu", "load_mock"],
  ["thư viện", "library_browse"],
  ["vật lý", "library_load"],
  ["số 3", "library_load"],
  ["tải file", "upload_file"],
  ["tải link", "upload_url"],
  ["tôi muốn gửi tài liệu", "upload_ask_source"],
  ["từ máy", "upload_file"],
  ["từ link", "upload_url"],
  ["bỏ qua", "skip_welcome"],
  ["đọc đi", "play"],
  ["tạm dừng", "pause"],
  ["đọc lại", "replay_block"],
  ["tua lui 10 giây", "seek"],
  ["phần này là gì", "ask_focus_block"],
  ["đơn giản hơn", "ask_simpler"],
  ["cho ví dụ", "ask_example"],
  ["tóm tắt", "summarize"],
  ["giúp đỡ", "help"],
  ["tắt mic", "mute"],
  ["bật mic", "unmute"],
  ["alo nghe rõ không", "free_chat"],
  ["tìm trên mạng định luật Newton", "web_search"],
  ["google giúp tôi tích phân", "web_search"],
  ["có tài liệu nào về phương trình", "web_search"],
  ["tải tài liệu vật lý và đọc đi cho tôi nghe", "agent_run"],
  ["tìm bài tập chất béo và tìm bài tập đại số", "agent_run"],
  ["xuất epub", "export_epub"],
  ["xuất braille", "export_braille"],
  ["nghe biểu đồ", "sonify_chart"],
];
let pass = 0, fail = 0;
const failures: string[] = [];
for (const [t, expected] of cases) {
  const r = parseVoiceCommand(t);
  if (r?.kind === expected) pass++;
  else { failures.push(`"${t}" -> ${r?.kind} (expected ${expected})`); fail++; }
}
console.log(`GRAMMAR_RESULT: ${pass}/${pass + fail} passed`);
if (failures.length) console.log("FAILURES:\\n" + failures.join("\\n"));
process.exit(fail > 0 ? 1 : 0);
""",
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            ["npx", "tsx", "test_grammar_selftest.ts"],
            cwd=ROOT / "frontend-next",
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("GRAMMAR_RESULT:"):
                count = line.split()[1]  # e.g. "22/22"
                p, total = count.split("/")
                if int(p) == int(total):
                    ok(f"J1 Grammar {count} passed")
                else:
                    fail(f"J1 Grammar {count} (some failed)")
                break
        else:
            fail(f"J1 grammar runner output unparseable: {result.stdout[:200]}")
        if result.returncode != 0 and result.stdout:
            for line in result.stdout.splitlines():
                if line.startswith("FAILURES:") or "->" in line:
                    print(f"  {line}")
    except subprocess.TimeoutExpired:
        fail("J0 grammar runner timeout")
    except Exception as e:
        fail(f"J0 grammar runner error: {e}")
    finally:
        if test_grammar.exists():
            test_grammar.unlink()

    # ============ K. TypeScript compile ============
    section("K. TypeScript")
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=ROOT / "frontend-next",
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
        # Only count actual errors, not hints
        errors = [l for l in result.stdout.splitlines() if "error TS" in l]
        if not errors:
            ok("K1 TypeScript: 0 errors")
        else:
            fail(f"K1 TypeScript: {len(errors)} errors:\n" + "\n".join(errors[:5]))
    except Exception as e:
        fail(f"K0 tsc runner error: {e}")

    # ============ Summary ============
    print()
    print("=" * 70)
    print(f"RESULT: PASS={PASS}  FAIL={FAIL}")
    print("=" * 70)
    if FAIL_DETAILS:
        print("\nFAIL details:")
        for d in FAIL_DETAILS:
            print(f"  - {d}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
