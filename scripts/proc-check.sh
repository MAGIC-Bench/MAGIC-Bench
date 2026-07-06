#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== python3 / run_dataset processes ==="
pgrep -af 'python3' | grep -v -e pgrep -e proc-check | cut -c1-100
echo "=== codex processes ==="
pgrep -af 'codex exec' | grep -v pgrep | grep -oE 'STAGE [0-9]+' | sort | uniq -c
echo "=== docker build / build tools ==="
pgrep -af 'docker build' | grep -v pgrep | grep -oE '\-t ref-[a-z-]+'
pgrep -afl 'cargo|pnpm|yarn|go build' 2>/dev/null | grep -v pgrep | grep -oiE 'cargo|pnpm|yarn|go build' | sort | uniq -c
echo "=== tail of rerun-failed.log ==="
tail -6 scripts/rerun-failed.log 2>/dev/null || echo "  (empty/buffered)"
echo "=== EXIT marker? ==="
grep -h '^EXIT=' scripts/rerun-failed.log 2>/dev/null || echo "  (none)"
