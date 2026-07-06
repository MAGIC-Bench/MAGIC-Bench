#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== process / exit ==="
if pgrep -f 'run_dataset' >/dev/null; then echo "  run_dataset: RUNNING"; else echo "  run_dataset: exited"; fi
grep -h '^EXIT=' scripts/rerun-failed.log 2>/dev/null || echo "  (no EXIT marker yet)"
echo "=== codex activity now (stage + effort) ==="
pgrep -af 'codex exec' 2>/dev/null | grep -oE 'STAGE [0-9]+|reasoning_effort=[a-z]+' | sort | uniq -c
echo "=== per-repo progress ==="
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("/mnt/d/code-bench/out")
ids = ["achno-gowall","activecm-rita-legacy","afnanenayet-diffsitter","alexhallam-tv",
       "anvilco-spectaql","graphql-hive-graphql-inspector","afuh-rick-and-morty-api",
       "supabase-postgres-meta","neilotoole-sq"]
for r in ids:
    s = out / r / "STATUS.json"
    if not s.exists():
        print(f"  {r:34} (no STATUS)"); continue
    st = json.loads(s.read_text(encoding="utf-8"))
    passed = sorted(int(k) for k,v in st.items() if v=="pass")
    fails = {k:v for k,v in st.items() if v!="pass"}
    hi = f"0-{passed[-1]}" if passed and passed==list(range(passed[0],passed[-1]+1)) else str(passed)
    tag = "DONE✓" if st.get("8")=="pass" else ""
    extra = "".join(f"  [stage{k} FAIL: {str(v)[:60]}]" for k,v in fails.items())
    print(f"  {r:34} pass {hi} {tag}{extra}")
PY
echo "=== ref images built (of the 9) ==="
docker images --format '{{.Repository}}' 2>/dev/null | grep -E 'ref-(achno|activecm|afnanenayet|alexhallam|anvilco|graphql|afuh|supabase|neilotoole)' | sort
