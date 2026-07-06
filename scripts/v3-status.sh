#!/usr/bin/env bash
# Quick status of the pilot-v3 run: daemon alive? per-repo stage progress? recent log.
cd /mnt/d/code-bench-v2 || exit 9
pid=$(pgrep -f run_dataset.py | tr '\n' ' ')
echo "=== daemon: ${pid:-DEAD} | mem $(free -h | awk 'NR==2{print $7}') free | $(date +%H:%M:%S) ==="
echo "=== per-repo STATUS.json ==="
for id in dosisod-refurb josephburnett-jd ogen-go-ogen bee-san-name-that-hash neilotoole-sq; do
  f="out/$id/STATUS.json"
  if [ -f "$f" ]; then
    st=$(python3 -c "import json;s=json.load(open('$f'));print(' '.join(f'{k}={v.split(chr(58))[0]}' for k,v in sorted(s.items(),key=lambda x:int(x[0]))))" 2>/dev/null)
    echo "  $id -> $st"
  else
    echo "  $id -> (not started)"
  fi
done
echo "=== docker now ==="; docker ps --format '  {{.Names}} {{.Status}}' 2>/dev/null | head
echo "=== tail pilot-v3.log ==="; tail -10 scripts/pilot-v3.log
