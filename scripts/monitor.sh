#!/usr/bin/env bash
echo "=== per-repo progress (STATUS.json) ==="
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("/mnt/d/code-bench/out")
for d in sorted(p for p in out.iterdir() if p.is_dir()):
    s = d / "STATUS.json"
    if not s.exists():
        continue
    st = json.loads(s.read_text(encoding="utf-8"))
    passed = sorted(int(k) for k, v in st.items() if v == "pass")
    fails = {k: v for k, v in st.items() if v != "pass"}
    if passed and passed == list(range(passed[0], passed[-1] + 1)):
        mark = f"stage 0-{passed[-1]} pass"
    else:
        mark = f"pass={passed}"
    extra = ""
    for k, v in fails.items():
        extra += f"  [stage{k} FAIL: {str(v)[:90]}]"
    print(f"  {d.name:34} {mark}{extra}")
PY
echo
echo "=== codex stage activity right now ==="
pgrep -af 'codex exec' | grep -oE 'STAGE [0-9]+ . [a-zA-Z +]+' | sort | uniq -c
echo "=== run_dataset processes ==="
pgrep -af 'run_dataset' | grep -v pgrep | grep -oE '\-\-jobs [0-9]+ --only [^ ]{0,40}'
echo
echo "=== ref- images built ==="
docker images --format '{{.Repository}}:{{.Tag}}' | grep '^ref-' | sort
echo "=== repos cloned ==="
ls -1 /mnt/d/code-bench/repos/ | tr '\n' ' '; echo
