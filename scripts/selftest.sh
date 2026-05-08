#!/bin/bash
# Self-test script — chạy mọi thứ có thể automate
# Phần voice / mic / UI cần human-in-loop, không test được ở đây.

set +e
PASS=0
FAIL=0
SKIP=0

ok() { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }
skip() { echo "[SKIP] $1"; SKIP=$((SKIP+1)); }

API=http://127.0.0.1:8000/api/v1
FE=http://127.0.0.1:3000

echo "======================================================================"
echo "VisionarySTEM SELF-TEST — Backend + Logic (no browser/mic)"
echo "======================================================================"

# ============ A. Servers up ============
echo
echo "=== A. Servers ==="

if curl -sf "$API/health" -m 3 -o /tmp/health.json 2>&1; then
  ok "A1 Backend /health responds"
  if grep -q "2.1.0" /tmp/health.json; then ok "A2 Backend version 2.1.0"; else fail "A2 version mismatch"; fi
  if grep -q "gemini-2.5-flash" /tmp/health.json; then ok "A3 Gemini model gemini-2.5-flash"; else fail "A3 model mismatch"; fi
else
  fail "A1 Backend down"
fi

if curl -sf -o /dev/null -w "%{http_code}" "$FE/" -m 3 | grep -q "200"; then
  ok "A4 Frontend responds 200"
else
  fail "A4 Frontend down"
fi

# ============ B. Mock data ============
echo
echo "=== B. Mock data ==="

curl -s "$API/mock/analyze" -m 30 -o /tmp/mock.json
BLOCKS=$(python -c "import json; print(len(json.load(open('/tmp/mock.json'))['content_blocks']))")
PAGES=$(python -c "import json; print(json.load(open('/tmp/mock.json'))['document_metadata']['total_pages'])")
FILE=$(python -c "import json; print(json.load(open('/tmp/mock.json'))['document_metadata']['filename'])")

if [ "$BLOCKS" = "13" ]; then ok "B1 Mock has 13 blocks"; else fail "B1 expected 13 blocks, got $BLOCKS"; fi
if [ "$PAGES" = "2" ]; then ok "B2 Mock has 2 pages"; else fail "B2 expected 2 pages, got $PAGES"; fi
if [ "$FILE" = "vat_ly_10_chuong_2_dinh_luat_newton.pdf" ]; then ok "B3 Mock filename"; else fail "B3 filename: $FILE"; fi

# Verify block diversity
TYPES=$(python -c "import json; r=json.load(open('/tmp/mock.json')); print(','.join(sorted(set(b['type'] for b in r['content_blocks']))))")
if echo "$TYPES" | grep -q "math"; then ok "B4 Has math blocks"; else fail "B4 no math"; fi
if echo "$TYPES" | grep -q "table"; then ok "B5 Has table block"; else fail "B5 no table"; fi
if echo "$TYPES" | grep -q "chart"; then ok "B6 Has chart block"; else fail "B6 no chart"; fi
if echo "$TYPES" | grep -q "figure"; then ok "B7 Has figure block"; else fail "B7 no figure"; fi
if echo "$TYPES" | grep -q "text"; then ok "B8 Has text blocks"; else fail "B8 no text"; fi

# Verify spatial_index has all blocks
COVER=$(python -c "
import json
r = json.load(open('/tmp/mock.json'))
all_ids = {b['id'] for b in r['content_blocks']}
mapped = set()
for region_ids in r['spatial_index']['regions'].values():
    mapped.update(region_ids)
print('1' if all_ids == mapped else f'missing={all_ids - mapped}, extra={mapped - all_ids}')
")
if [ "$COVER" = "1" ]; then ok "B9 spatial_index covers all blocks"; else fail "B9 spatial_index: $COVER"; fi

# ============ C. Library ============
echo
echo "=== C. Library (6 samples) ==="

curl -s "$API/library" -m 5 -o /tmp/lib.json
COUNT=$(python -c "import json; print(json.load(open('/tmp/lib.json'))['count'])")
if [ "$COUNT" = "6" ]; then ok "C1 Library count 6"; else fail "C1 count: $COUNT"; fi

for slug in physics calculus linear_algebra chemistry statistics wave_physics; do
  if grep -q "\"$slug\"" /tmp/lib.json; then ok "C2 slug $slug present"; else fail "C2 slug $slug missing"; fi
done

# Test library file existence
for f in sample_physics.pdf sample_calculus.pdf sample_linear_algebra.pdf sample_chemistry.pdf sample_statistics.pdf sample_wave_physics.pdf; do
  if [ -f "/d/VisionarySTEM/tests/sample_data/$f" ]; then ok "C3 file $f exists"; else fail "C3 file $f missing"; fi
done

# ============ D. TTS Aoede ============
echo
echo "=== D. TTS ==="

curl -s -X POST "$API/tts/v2/speak?text=Test+gi%E1%BB%8Dng&voice=Aoede&mood=warm" -o /tmp/test.wav -w "%{http_code} %{size_download}\n" -m 30 > /tmp/tts_meta.txt
HTTP=$(awk '{print $1}' /tmp/tts_meta.txt)
SIZE=$(awk '{print $2}' /tmp/tts_meta.txt)
if [ "$HTTP" = "200" ]; then ok "D1 TTS responds 200"; else fail "D1 TTS HTTP=$HTTP"; fi
if [ "$SIZE" -gt 1000 ]; then ok "D2 TTS WAV size $SIZE bytes"; else fail "D2 size too small: $SIZE"; fi
# Verify WAV header
if head -c 4 /tmp/test.wav | grep -q "RIFF"; then ok "D3 WAV header valid"; else fail "D3 not WAV"; fi

# ============ E. /assist (no doc) ============
echo
echo "=== E. /assist (general Q&A, no doc) ==="

cat > /tmp/assist_q1.json << 'EOF'
{"question":"Niu-ton la ai?"}
EOF
RESP=$(curl -s -X POST "$API/assist" -H "Content-Type: application/json" --data-binary @/tmp/assist_q1.json -m 30)
LEN=$(echo "$RESP" | python -c "import sys,json; print(len(json.load(sys.stdin)['reply_text']))")
if [ "$LEN" -gt 100 ]; then ok "E1 /assist reply length $LEN >100 chars"; else fail "E1 reply too short: $LEN"; fi
# Check for English math reading (should NOT contain "F equals")
if echo "$RESP" | grep -qi "F equals"; then fail "E2 Contains English math (BAD)"; else ok "E2 No English math reading"; fi

# ============ F. /chat (with mock doc) ============
echo
echo "=== F. /chat (tutor with mock doc) ==="

# Trigger mock load first to register doc
curl -s "$API/mock/analyze" -o /dev/null -m 30

cat > /tmp/chat_q1.json << 'EOF'
{"document_id":"mock_doc","session_id":"selftest_1","message":"ban co the lam duoc gi voi tai lieu nay?","voice_mode":false}
EOF
RESP=$(curl -s -X POST "$API/chat" -H "Content-Type: application/json" --data-binary @/tmp/chat_q1.json -m 60)
LEN=$(echo "$RESP" | python -c "import sys,json; print(len(json.load(sys.stdin)['reply_text']))")
if [ "$LEN" -gt 200 ]; then ok "F1 /chat reply length $LEN >200 chars"; else fail "F1 reply too short: $LEN"; fi

# Check NO block_001 in reply text
HAS_BLOCK_ID=$(echo "$RESP" | python -c "
import sys, json, re
r = json.load(sys.stdin)
text = r['reply_text']
ids = re.findall(r'block_\d+', text)
print('YES' if ids else 'NO')
")
if [ "$HAS_BLOCK_ID" = "NO" ]; then ok "F2 No 'block_xxx' in reply text"; else fail "F2 Reply contains block IDs"; fi

# Check cited_blocks present (internal mapping for frontend)
CITED=$(echo "$RESP" | python -c "import sys,json; print(len(json.load(sys.stdin)['cited_blocks']))")
if [ "$CITED" -gt 0 ]; then ok "F3 cited_blocks tracked internally ($CITED items)"; else fail "F3 no cited_blocks"; fi

# Check followups
FOLLOWUPS=$(echo "$RESP" | python -c "import sys,json; print(len(json.load(sys.stdin)['suggested_followups']))")
if [ "$FOLLOWUPS" -ge 1 ]; then ok "F4 Has $FOLLOWUPS suggested followups"; else fail "F4 no followups"; fi

# ============ G. URL upload validation ============
echo
echo "=== G. /analyze-url validation ==="

# G1: Bad protocol
RESP=$(curl -s -X POST "$API/analyze-url" -H "Content-Type: application/json" -d '{"url":"ftp://example.com/x.pdf"}' -w "\n%{http_code}" -m 10)
HTTP=$(echo "$RESP" | tail -n1)
if [ "$HTTP" = "400" ]; then ok "G1 ftp:// rejected (400)"; else fail "G1 ftp:// got $HTTP"; fi

# G2: Empty URL
RESP=$(curl -s -X POST "$API/analyze-url" -H "Content-Type: application/json" -d '{"url":""}' -w "\n%{http_code}" -m 10)
HTTP=$(echo "$RESP" | tail -n1)
if [ "$HTTP" = "400" ]; then ok "G2 Empty URL rejected"; else fail "G2 empty got $HTTP"; fi

# ============ H. Library load (real Gemini analyze) ============
echo
echo "=== H. Library load — physics ==="

START=$(date +%s)
RESP=$(curl -s -X POST "$API/library/physics/analyze" -m 60)
END=$(date +%s)
ELAPSED=$((END-START))
BLOCKS=$(echo "$RESP" | python -c "import sys,json; print(len(json.load(sys.stdin)['content_blocks']))" 2>/dev/null || echo "0")
if [ "$BLOCKS" -gt 0 ]; then ok "H1 Library physics → $BLOCKS blocks (${ELAPSED}s)"; else fail "H1 no blocks: $RESP"; fi

# ============ I. /chat/stream (SSE) ============
echo
echo "=== I. /chat/stream (SSE) ==="

cat > /tmp/stream_q.json << 'EOF'
{"document_id":"mock_doc","session_id":"selftest_stream","message":"tom tat ngan gon"}
EOF
# Use timeout to limit SSE
curl -s -X POST "$API/chat/stream" -H "Content-Type: application/json" --data-binary @/tmp/stream_q.json -m 60 -N > /tmp/stream.txt 2>&1
if grep -q "event: token" /tmp/stream.txt; then ok "I1 SSE token events received"; else fail "I1 no token events"; fi
if grep -q "event: done" /tmp/stream.txt; then ok "I2 SSE done event received"; else fail "I2 no done event"; fi

echo
echo "======================================================================"
echo "RESULT: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "======================================================================"
exit $FAIL
