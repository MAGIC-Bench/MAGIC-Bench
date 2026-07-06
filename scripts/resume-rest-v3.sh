#!/usr/bin/env bash
# Resume remaining 3 pilot-v3 repos from the right stage after fixes:
#   ogen-go-ogen        -> stage7 pass with drop_threshold=0.15 -> resume from stage7
#   bee-san-name-that-hash -> stage1 fail (deident false positive) -> resume from stage1
#   neilotoole-sq       -> stage0 image OK, but Version=codebench caused panic -> rebuild image, resume from stage0 build only
export PATH="$HOME/.local/bin:$PATH"
export GOPROXY=goproxy.cn,direct
cd /mnt/d/code-bench-v2 || exit 9

pkill -f run_dataset.py 2>/dev/null; pkill -9 -f 'codex exec' 2>/dev/null; sleep 2

python3 - <<'PY'
import json, pathlib

# ogen: stage7 already had 58/65 pass (11% drop); drop_threshold now 0.15 -> retry from stage7
for rid, frm in [("ogen-go-ogen", 7), ("bee-san-name-that-hash", 1)]:
    sp = pathlib.Path("out") / rid / "STATUS.json"
    st = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    st = {k: v for k, v in st.items() if int(k) < frm}
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(f"{rid}: resume from stage {frm}")

# sq: need to rebuild the Docker image (Version fix), then re-run from stage0 build step only
# Reset sq status to before stage0-build so stage0 reruns the docker build
rid = "neilotoole-sq"
sp = pathlib.Path("out") / rid / "STATUS.json"
st = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
# Keep stage 0 as pass only if we DON'T need to rebuild; we DO need to rebuild so reset to {}
# But stage0 ingest also clones the repo - repos/neilotoole-sq exists, so it will skip clone.
# We just need stage0 to re-run the build step. stage0 is not idempotent in STATUS (it's "pass")
# so we reset stage0 to force a rerun.
st_new = {}  # full reset: stage0 will re-run (clone already done, will skip clone, redo build)
sp.write_text(json.dumps(st_new, indent=2), encoding="utf-8")
print(f"{rid}: full reset -> stage0 re-runs (Docker rebuild with fixed Version=0.0.0-codebench)")
PY

setsid nohup env PYTHONUNBUFFERED=1 GOPROXY=goproxy.cn,direct PATH="$HOME/.local/bin:$PATH" \
  python3 -u run_dataset.py --manifest dataset/pilot-v3.manifest.json --agent codex \
  --only ogen-go-ogen,bee-san-name-that-hash,neilotoole-sq --from 0 --to 8 --jobs 1 \
  > scripts/pilot-v3-rest2.log 2>&1 < /dev/null &
disown
sleep 5
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "free mem: $(free -h | awk 'NR==2{print $7}') available"
echo "=== first log lines ==="; head -15 scripts/pilot-v3-rest2.log
