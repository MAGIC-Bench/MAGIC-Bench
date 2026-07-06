#!/usr/bin/env bash
# Stop the slow xhigh daemon + kill ruff's runaway build, relaunch the 14 (ruff removed) at high.
# yamllint (s8 DONE) skips; carapace (s0 pass) resumes from s1; the rest run fresh with high + timeout.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f run_dataset.py 2>/dev/null
pkill -9 -f 'codex exec' 2>/dev/null
docker ps -q 2>/dev/null | xargs -r docker kill >/dev/null 2>&1   # kill ruff's 44-min build container
pkill -9 -x cargo 2>/dev/null
sleep 3
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 \
    > scripts/rerun-v2.log 2>&1 < /dev/null &
disown
sleep 4
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "log:"; head -3 scripts/rerun-v2.log
