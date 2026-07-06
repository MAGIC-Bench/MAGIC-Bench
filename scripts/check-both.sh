#!/usr/bin/env bash
echo "=== cherrybomb package contents (impl written?) ==="
ls -1 /mnt/d/code-bench/out/exam-packages/blst-security-cherrybomb/
echo "=== cherrybomb Dockerfile ==="
cat /mnt/d/code-bench/out/exam-packages/blst-security-cherrybomb/Dockerfile 2>/dev/null
echo
echo "=== pilot-v2 daemon alive? ==="
pgrep -af run_dataset.py | grep -v pgrep | cut -c1-70 || echo "  NOT running (stopped)"
echo "=== rerun-v2.log tail (where it stopped) ==="
tail -6 /mnt/d/code-bench/scripts/rerun-v2.log 2>/dev/null
echo "=== pilot-v2 14-repo status ==="
cd /mnt/d/code-bench || exit 9
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("out")
ids = [r["id"] for r in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]
done = 0
for r in ids:
    s = out / r / "STATUS.json"
    st = json.loads(s.read_text()) if s.exists() else {}
    p = sorted(int(k) for k, v in st.items() if v == "pass")
    f = [k for k, v in st.items() if v != "pass"]
    tag = "DONE" if st.get("8") == "pass" else (f"stage{f[0]} FAIL" if f else (f"s{p[-1]}" if p else "-"))
    if st.get("8") == "pass": done += 1
    print(f"  {r:34} {tag}")
print(f"  => {done}/{len(ids)} done")
PY
