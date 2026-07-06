#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9

python3 -c "
import json, pathlib
sp = pathlib.Path('out/bee-san-name-that-hash/STATUS.json')
st = json.loads(sp.read_text())
st = {k: v for k, v in st.items() if int(k) < 6}
sp.write_text(json.dumps(st, indent=2))
print('reset to stages:', list(st.keys()))
"

setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --only bee-san-name-that-hash --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3-bee-san.log 2>&1 < /dev/null &
disown
sleep 3
echo "bee-san pid: $(pgrep -f run_dataset.py | grep -v $$ | tr '\n' ' ')"
head -5 scripts/pilot-v3-bee-san.log
