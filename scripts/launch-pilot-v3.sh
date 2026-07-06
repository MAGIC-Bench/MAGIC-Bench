#!/usr/bin/env bash
# pilot-v3: 5 repos (1 per scenario) through Stage 0-8, docker mode, codex@high, jobs=1.
# 7.6GB WSL -> sequential to avoid OOM. Detached daemon survives wsl-session churn.
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9
pkill -f run_dataset.py 2>/dev/null; pkill -9 -f 'codex exec' 2>/dev/null; sleep 2
mkdir -p scripts out repos
setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -12 scripts/pilot-v3.log
