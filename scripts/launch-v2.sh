#!/usr/bin/env bash
# Full Stage 0-8 run of pilot-v2 (15 repos), detached daemon + jobs=1 + xhigh.
# Detached (setsid/nohup) so it survives wsl-session churn; jobs=1 so it can't OOM the 7.6GB VM.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f 'run_dataset.py' 2>/dev/null
sleep 1
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 \
    > scripts/rerun-v2.log 2>&1 < /dev/null &
disown
sleep 4
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "log head:"; head -4 scripts/rerun-v2.log
