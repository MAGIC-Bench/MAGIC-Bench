#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== all 14 status ==="
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("out")
for r in [x["id"] for x in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]:
    s = out / r / "STATUS.json"
    st = json.loads(s.read_text()) if s.exists() else {}
    p = sorted(int(k) for k, v in st.items() if v == "pass")
    f = {k: v for k, v in st.items() if v != "pass"}
    line = f"  {r:34} pass<= s{p[-1] if p else '-'}"
    for k, v in f.items():
        line += f"   [stage{k}: {str(v)[:75]}]"
    print(line)
PY
echo "=== recent log (last 12) ==="
tail -12 scripts/rerun-v2.log 2>/dev/null
