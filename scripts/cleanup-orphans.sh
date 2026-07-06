#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 0
docker ps -q 2>/dev/null | xargs -r docker kill >/dev/null 2>&1
pkill -9 -x cargo 2>/dev/null
pkill -9 -f 'pip ' 2>/dev/null
pkill -9 -f pnpm 2>/dev/null
pkill -9 -f yarn 2>/dev/null
sleep 2
echo -n "daemon alive: "; pgrep -f run_dataset.py >/dev/null && echo YES || echo "NO(!)"
echo -n "orphan build procs now: "; pgrep -cE 'cargo|pnpm|yarn' 2>/dev/null; echo
echo -n "free mem: "; free -h | awk 'NR==2{print $7" available"}'
echo "--- log tail (where it is) ---"; tail -3 scripts/rerun-v2.log
exit 0
