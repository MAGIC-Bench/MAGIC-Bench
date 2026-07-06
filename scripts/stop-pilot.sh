#!/usr/bin/env bash
# Stop the pilot cleanly. Run as a FILE so this shell's cmdline ("bash stop-pilot.sh") does not
# contain the patterns below -> pkill -f won't kill the checker itself.
pkill -f run_dataset.py 2>/dev/null
sleep 1
pkill -9 -f 'codex exec' 2>/dev/null
sleep 1
docker ps -q 2>/dev/null | xargs -r docker kill >/dev/null 2>&1
sleep 2
echo "run_dataset left: $(pgrep -fc run_dataset.py)"
echo "codex left:       $(pgrep -fc 'codex exec')"
echo "containers left:  $(docker ps -q | wc -l)"
echo "mem free:         $(free -h | awk 'NR==2{print $7}')"
echo "=== where it stopped (last log lines) ==="
tail -6 /mnt/d/code-bench-v2/scripts/pilot-v3.log
echo "=== per-repo final STATUS ==="
for id in dosisod-refurb josephburnett-jd ogen-go-ogen bee-san-name-that-hash neilotoole-sq; do
  f="/mnt/d/code-bench-v2/out/$id/STATUS.json"
  [ -f "$f" ] && echo "  $id: $(python3 -c "import json;print(sorted(json.load(open('$f')).items(),key=lambda x:int(x[0])))" 2>/dev/null)" || echo "  $id: (not started)"
done
