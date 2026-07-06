#!/usr/bin/env bash
# FRESH pilot-v3: wipe prior (flawed) out/ + repos/ clones, re-run all 5 through Stage 0-8 with the
# new quality logic (gate_stage6 hard-block, argv-binary guard, fairness/contract-consistency rules).
# docker mode, codex@high, jobs=1 (7.6GB WSL -> sequential, no OOM). Detached daemon.
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9
pkill -f run_dataset.py 2>/dev/null
pkill -9 -f 'codex exec' 2>/dev/null
docker ps -q 2>/dev/null | xargs -r docker kill >/dev/null 2>&1
sleep 2
rm -rf out repos 2>/dev/null           # pristine: re-clone + re-generate everything
mkdir -p out repos scripts
setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "out/ + repos/ wiped clean"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -10 scripts/pilot-v3.log
