#!/usr/bin/env bash
echo "=== dirs under ~/.codex ==="
find ~/.codex -maxdepth 3 -type d 2>/dev/null | head -30
echo "=== newest 5 session jsonl ==="
find ~/.codex -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -5 | cut -d' ' -f2-
NEWEST=$(find ~/.codex -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
echo "=== first record of newest session ($NEWEST) ==="
head -1 "$NEWEST" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -50
echo "=== model / reasoning mentions across newest session ==="
grep -oiE '"model"[^,}]{0,40}|"effort"[^,}]{0,30}|"reasoning[^,}]{0,40}|gpt-5[a-z0-9-]*|o[34][a-z-]*' "$NEWEST" 2>/dev/null | sort | uniq -c | sort -rn | head -15
