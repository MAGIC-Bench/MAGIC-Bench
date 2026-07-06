#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
cd /tmp || exit 9
timeout 90 codex exec -c model_reasoning_effort=xhigh --skip-git-repo-check \
    --sandbox workspace-write "Reply with exactly: ok" </dev/null >/tmp/xhigh_out.txt 2>&1
echo "codex rc=$?"
NEWEST=$(find ~/.codex/sessions -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
echo "newest session: $(basename "$NEWEST")"
echo -n "recorded reasoning_effort: "; grep -o '"reasoning_effort":"[a-z]*"' "$NEWEST" 2>/dev/null | sort | uniq -c
echo -n "recorded model: "; grep -oE '"model":"[^"]*"' "$NEWEST" 2>/dev/null | sort | uniq -c | head -1
