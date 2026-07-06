#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
now=$(date +%s)
echo "=== any docker run (replay) / codex now ==="
pgrep -afl 'docker run|codex exec' 2>/dev/null | grep -v pgrep | grep -oiE 'docker run|codex exec' | sort | uniq -c
echo "=== sq out/ files by recency (top 6) ==="
ls -lt --time-style=+%s out/neilotoole-sq/ 2>/dev/null | awk -v now="$now" 'NR>1 && NR<=7 {print "  "(now-$6)"s ago  "$7}'
echo "=== sq stage5 ledger / drafts present? ==="
for f in _drafts_round.json 05_coverage-ledger.json 05_tests; do
  if [ -e "out/neilotoole-sq/$f" ]; then echo "  $f : present ($(( now - $(stat -c%Y "out/neilotoole-sq/$f") ))s ago)"; else echo "  $f : (none yet)"; fi
done
echo "=== count of frozen test cases so far ==="
ls out/neilotoole-sq/05_tests/ 2>/dev/null | wc -l
echo "=== rerun2.log tail ==="
tail -4 scripts/rerun2.log 2>/dev/null || echo "  (buffered/empty)"
