#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
pgrep -f run_dataset.py >/dev/null && echo "DAEMON ALIVE" || echo "daemon dead"
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("out")
ids = [r["id"] for r in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]
for r in ids:
    s = out / r / "STATUS.json"
    if not s.exists():
        print(f"  {r:34} (not started)"); continue
    st = json.loads(s.read_text(encoding="utf-8"))
    passed = sorted(int(k) for k, v in st.items() if v == "pass")
    fails = [k for k, v in st.items() if v != "pass"]
    tag = "DONE" if st.get("8") == "pass" else (f"stage{fails[0]} FAIL" if fails else f"s{passed[-1] if passed else '-'}")
    print(f"  {r:34} {tag}")
PY
