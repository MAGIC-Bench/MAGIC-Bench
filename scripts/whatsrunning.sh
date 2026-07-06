#!/usr/bin/env bash
echo "=== active pipeline processes ==="
pgrep -af 'run_dataset|codex exec|docker build|stage' | grep -v -e pgrep -e whatsrunning | cut -c1-120
if [ -z "$(pgrep -f 'run_dataset')" ]; then echo "  (no run_dataset process — batch runs have exited)"; fi
echo
echo "=== background run exit markers ==="
echo -n "canary-goawk.log : "; grep -h '^EXIT=' /mnt/d/code-bench/scripts/canary-goawk.log 2>/dev/null || echo "(no EXIT line / still running or truncated)"
echo -n "pilot-rest.log   : "; grep -h '^EXIT=' /mnt/d/code-bench/scripts/pilot-rest.log 2>/dev/null || echo "(no EXIT line / still running or truncated)"
echo
echo "=== current per-repo final stage ==="
python3 - <<'PY'
import json, pathlib
out = pathlib.Path('/mnt/d/code-bench/out')
done = part = 0
for d in sorted(p for p in out.iterdir() if p.is_dir()):
    s = d / "STATUS.json"
    if not s.exists():
        continue
    st = json.loads(s.read_text(encoding="utf-8"))
    if st.get("8") == "pass":
        done += 1
    else:
        part += 1
print(f"  完成(stage8 pass): {done}    未完成: {part}")
PY
