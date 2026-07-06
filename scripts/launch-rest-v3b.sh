#!/usr/bin/env bash
# Re-launch remaining 3 repos:
#   ogen-go-ogen:           stage7 failed 15% drop  -> reset to stage5 (keep 0-4), regenerate tests
#   bee-san-name-that-hash: stage0 failed TLS        -> fresh (Docker mirror now configured)
#   neilotoole-sq:          stage7 failed 86% drop  -> reset to stage5 (keep 0-4), regenerate tests
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9

pkill -f run_dataset.py 2>/dev/null; pkill -9 -f 'codex exec' 2>/dev/null; sleep 2

python3 - <<'PY'
import json, pathlib

resets = {
    "ogen-go-ogen":           5,   # keep stages 0-4, redo 5-8
    "neilotoole-sq":          5,   # keep stages 0-4, redo 5-8
    "bee-san-name-that-hash": 0,   # fresh
}
for rid, keep_below in resets.items():
    base = pathlib.Path("out") / rid
    sp   = base / "STATUS.json"
    st   = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    st   = {k: v for k, v in st.items() if int(k) < keep_below}
    base.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(f"{rid}: keep stages {list(st.keys())} -> resume from stage {keep_below}")
PY

setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --only ogen-go-ogen,bee-san-name-that-hash,neilotoole-sq --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3-rest.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -15 scripts/pilot-v3-rest.log
