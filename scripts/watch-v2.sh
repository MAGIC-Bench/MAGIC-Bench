#!/usr/bin/env bash
# Live dashboard for PILOT v2.  Windows:  wsl bash /mnt/d/code-bench/scripts/watch-v2.sh
# Ctrl-C to quit. Reads the pilot-v2 manifest, so it tracks the right 15 repos.
cd /mnt/d/code-bench || exit 9
INTERVAL="${1:-5}"
while true; do
  clear
  echo "=============== codegen-bench PILOT v2 monitor ==============="
  printf "time: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')"
  if pgrep -f 'run_dataset' >/dev/null 2>&1; then
    echo "orchestrator: RUNNING ($(pgrep -af run_dataset 2>/dev/null | grep -oE '\-\-jobs [0-9]+' | head -1))"
  else
    echo "orchestrator: not running   $(grep -h '^EXIT=' scripts/rerun-v2.log 2>/dev/null | tail -1)"
  fi
  active=""
  for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
    c=$(readlink "/proc/$pid/cwd" 2>/dev/null); [ -n "$c" ] && active=$(basename "$c")
  done
  if [ -z "$active" ]; then
    img=$(pgrep -af 'docker (build|run)' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | head -1); [ -n "$img" ] && active="${img#ref-}"
  fi
  cx=$(pgrep -af 'codex exec' 2>/dev/null | grep -oE 'STAGE [0-9]+' | head -1)
  db=$(pgrep -af 'docker build' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | head -1)
  echo "active: repo[${active:-none}]  codex[${cx:-idle}]  build[${db:-none}]"
  echo "-------------------------------------------------------------"
  ACTIVE="$active" python3 - <<'PY'
import json, os, pathlib
ids = [r["id"] for r in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]
out = pathlib.Path("out"); active = os.environ.get("ACTIVE", ""); done = 0
for r in ids:
    s = out / r / "STATUS.json"
    st = json.loads(s.read_text(encoding="utf-8")) if s.exists() else {}
    passed = sorted(int(k) for k, v in st.items() if v == "pass")
    hi = passed[-1] if passed else -1
    fails = [k for k, v in st.items() if v != "pass"]
    if st.get("8") == "pass":
        icon, done = "[DONE]", done + 1
    elif r == active:
        icon = "[>> ]"
    elif fails:
        icon = "[FAIL]"
    else:
        icon = "[ . ]" if passed else "[   ]"
    bar = "".join("#" if i <= hi else "." for i in range(9))
    note = f"  stage{fails[0]} stop" if (fails and st.get("8") != "pass") else ""
    print(f" {icon} {r:34s} {bar} s{hi if hi>=0 else '-'}{note}")
print("-------------------------------------------------------------")
print(f" full exams: {done}/{len(ids)}")
PY
  echo "--- recent log ---"
  tail -3 scripts/rerun-v2.log 2>/dev/null | cut -c1-60 | sed 's/^/  /'
  echo "(refresh ${INTERVAL}s  -  Ctrl-C to quit)"
  sleep "$INTERVAL"
done
