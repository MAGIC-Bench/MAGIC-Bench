#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== processes: run_dataset / bash rerun2 / python / codex ==="
pgrep -af 'run_dataset|rerun2.sh|codex exec' 2>/dev/null | grep -v -e pgrep -e diag-resume | cut -c1-100
echo "  (none above = all dead)"
echo "=== zombies / defunct ==="
ps -eo pid,ppid,stat,comm 2>/dev/null | awk '$3 ~ /Z/ {print "  ZOMBIE "$0}' | head
echo "=== rerun2.log (full) ==="
cat scripts/rerun2.log 2>/dev/null | tail -25
echo "=== EXIT markers ==="
grep -h '^EXIT=' scripts/rerun2.log 2>/dev/null || echo "  (no EXIT in rerun2.log)"
echo "=== memory ==="
free -h | head -2
echo "=== sq stage5 progress (frozen tests / ledger) ==="
echo "  05_tests cases: $(ls out/neilotoole-sq/05_tests/*.json 2>/dev/null | wc -l)"
echo "  ledger: $([ -f out/neilotoole-sq/05_coverage-ledger.json ] && echo present || echo none)"
