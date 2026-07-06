#!/usr/bin/env bash
# Validation re-run: jd + refurb through Stage 0-8 with the generation-side fixes.
# Resets STATUS so stage>=5 RE-RUNS (regenerate golden with the #1 self-ref backstop + new stage5
# prompt rules), reusing stage0-4 when the repo is still cloned. jobs=1. Detached daemon.
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9
pkill -f run_dataset.py 2>/dev/null; pkill -9 -f 'codex exec' 2>/dev/null; sleep 2

python3 - <<'PY'
import json, pathlib
for rid in ("dosisod-refurb", "josephburnett-jd"):
    base = pathlib.Path("out") / rid
    sp = base / "STATUS.json"
    has_repo = (pathlib.Path("repos") / rid).exists() and any((pathlib.Path("repos") / rid).iterdir())
    has_tests = (base / "05_tests").exists() and any((base / "05_tests").glob("*.json"))
    st = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    if not has_repo:
        st, frm = {}, 0                                              # re-clone from stage0
    elif has_tests and st.get("5") == "pass":
        st, frm = {k: v for k, v in st.items() if int(k) < 6}, 6     # (2) resume from stage6, reuse golden
    else:
        st, frm = {k: v for k, v in st.items() if int(k) < 5}, 5     # stage5 incomplete -> regenerate
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(f"{rid}: resume from stage {frm}  (stage5_done={st.get('5') == 'pass'}, has_tests={has_tests})")
PY

setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --only dosisod-refurb,josephburnett-jd --from 0 --to 8 --jobs 2 \
  > scripts/pilot-v3.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -10 scripts/pilot-v3.log
