#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== daemon ==="; pgrep -af run_dataset.py | grep -v pgrep | cut -c1-60 || echo "  DEAD"
echo "=== active right now ==="
for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
  c=$(readlink "/proc/$pid/cwd" 2>/dev/null); [ -n "$c" ] && echo "  codex in: $(basename "$c")"
done
pgrep -af 'docker build' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | sed 's/^/  building: /'
pgrep -afl 'pip|cargo|docker build' 2>/dev/null | grep -v pgrep | grep -oiE 'pip|cargo|docker build' | sort | uniq -c | sed 's/^/  /'
echo "=== full rerun-v2.log (every step) ==="
cat scripts/rerun-v2.log 2>/dev/null
echo "=== yamllint build attempts (baseline) ==="
python3 -c "import json,pathlib; b=pathlib.Path('out/adrienverge-yamllint/00_baseline/baseline.json'); print(' ',{k:json.loads(b.read_text())[k] for k in ('build_attempts','build_repair_errors','image') if k in json.loads(b.read_text())} if b.exists() else 'no baseline yet')"
echo "=== ruff STATUS (should be absent=queued) ==="
ls out/astral-sh-ruff/STATUS.json 2>/dev/null && echo "  has STATUS" || echo "  no STATUS (not started = queued behind yamllint)"
