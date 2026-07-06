#!/usr/bin/env bash
# Bump to jobs=2 (2 repos in parallel, ~2x throughput). Safer than v1's fatal jobs=3 because:
# ruff removed + 12min build timeout caps runaway builds + high (not xhigh). yamllint stays DONE.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f run_dataset.py 2>/dev/null
pkill -9 -f 'codex exec' 2>/dev/null
docker ps -q 2>/dev/null | xargs -r docker kill >/dev/null 2>&1
sleep 3
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 2 \
    > scripts/rerun-v2.log 2>&1 < /dev/null &
disown
sleep 4
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
head -4 scripts/rerun-v2.log
