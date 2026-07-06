#!/usr/bin/env bash
# Launch remaining 3 pilot-v3 repos (ogen-go-ogen, bee-san-name-that-hash, neilotoole-sq)
# jobs=1: all 3 need Docker builds; Go parallel builds risk OOM.
# neilotoole-sq has build_timeout_s=1800 in manifest (was 720s timeout before).
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9

pkill -f run_dataset.py 2>/dev/null; pkill -9 -f 'codex exec' 2>/dev/null; sleep 2

# All 3 are fresh starts — no STATUS.json yet, no repos cloned.
for rid in ogen-go-ogen bee-san-name-that-hash neilotoole-sq; do
    echo "$rid: fresh start from stage0"
done

setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --only ogen-go-ogen,bee-san-name-that-hash,neilotoole-sq --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3-rest.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -10 scripts/pilot-v3-rest.log
