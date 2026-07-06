#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== daemon + where it is now ==="
pgrep -f run_dataset.py >/dev/null && echo "  ALIVE" || echo "  DEAD"
tail -6 scripts/rerun-v2.log 2>/dev/null
echo
for id in adrienverge-yamllint astral-sh-ruff; do
  echo "########## $id ##########"
  echo "STATUS: $(tr -d '\n ' < out/$id/STATUS.json 2>/dev/null)"
  echo "--- Dockerfile.codebench FROM/RUN ---"
  grep -nE '^\s*(FROM|RUN)' "repos/$id/Dockerfile.codebench" 2>/dev/null | cut -c1-150
  echo "--- docker_build_error tail ---"
  python3 - "$id" <<'PY'
import json,sys,pathlib
b=pathlib.Path(f"/mnt/d/code-bench/out/{sys.argv[1]}/00_baseline/baseline.json")
if b.exists():
    d=json.loads(b.read_text(encoding="utf-8"))
    print((d.get("docker_build_error") or d.get("error") or "(no build error recorded)")[-900:])
else:
    print("(no baseline.json)")
PY
  echo
done
