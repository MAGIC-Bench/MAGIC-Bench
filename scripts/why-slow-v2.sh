#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
now=$(date +%s)
echo "=== now: $(date '+%H:%M:%S') ==="
echo "=== daemon uptime ==="
pid=$(pgrep -f run_dataset.py | head -1)
if [ -n "$pid" ]; then echo "  pid=$pid  running for $(ps -o etimes= -p "$pid" | tr -d ' ')s"; else echo "  DEAD"; fi
echo "=== rerun-v2.log (full, with file age) ==="
[ -f scripts/rerun-v2.log ] && echo "  (last write $(( now - $(stat -c%Y scripts/rerun-v2.log) ))s ago)"
cat scripts/rerun-v2.log 2>/dev/null
echo "=== active now ==="
for p in $(pgrep -f 'codex exec' 2>/dev/null); do c=$(readlink /proc/$p/cwd 2>/dev/null); [ -n "$c" ] && echo "  codex@ $(basename "$c")  (running $(ps -o etimes= -p "$p"|tr -d ' ')s)"; done
pgrep -af 'docker build' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | sed 's/^/  building /'
pgrep -af 'docker run' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | sed 's/^/  replay-run /'
echo "=== where stuck: yamllint stage5 detail ==="
echo "  frozen tests: $(ls out/adrienverge-yamllint/05_tests/*.json 2>/dev/null | wc -l)"
echo "  drafts file age: $([ -f out/adrienverge-yamllint/_drafts_round.json ] && echo $(( now - $(stat -c%Y out/adrienverge-yamllint/_drafts_round.json) ))s || echo none)"
echo "=== all 15 ==="
python3 - <<'PY'
import json, pathlib
out=pathlib.Path("out")
for r in [x["id"] for x in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]:
    s=out/r/"STATUS.json"; st=json.loads(s.read_text()) if s.exists() else {}
    p=sorted(int(k) for k,v in st.items() if v=="pass"); f=[k for k,v in st.items() if v!="pass"]
    print(f"  {r:34} {'s'+str(p[-1]) if p else '-':4} {'FAIL'+f[0] if f else ''}")
PY
