#!/usr/bin/env bash
# Live dashboard for the codegen-bench pilot.
#   Run from Windows:   wsl bash /mnt/d/code-bench/scripts/watch-pilot.sh
#   Or inside WSL:      bash /mnt/d/code-bench/scripts/watch-pilot.sh [interval_seconds]
# Ctrl-C to quit. Default refresh = 5s.
cd /mnt/d/code-bench || exit 9
INTERVAL="${1:-5}"

while true; do
  clear
  echo "================= codegen-bench pilot monitor ================="
  printf "time: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')"

  # orchestrator state
  if pgrep -f 'run_dataset' >/dev/null 2>&1; then
    j=$(pgrep -af 'run_dataset' 2>/dev/null | grep -oE '\-\-jobs [0-9]+' | head -1)
    echo "orchestrator: RUNNING (${j:-?})"
  else
    ex=$(grep -h '^EXIT=' scripts/rerun*.log 2>/dev/null | tail -1)
    echo "orchestrator: not running   ${ex}"
  fi

  # what's active right now
  active=""
  for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
    c=$(readlink "/proc/$pid/cwd" 2>/dev/null); [ -n "$c" ] && active=$(basename "$c")
  done
  if [ -z "$active" ]; then
    img=$(pgrep -af 'docker (build|run)' 2>/dev/null | grep -oE 'ref-[a-z-]+' | head -1)
    [ -n "$img" ] && active="${img#ref-}"
  fi
  cx=$(pgrep -af 'codex exec' 2>/dev/null | grep -oE 'STAGE [0-9]+' | head -1)
  db=$(pgrep -af 'docker build' 2>/dev/null | grep -oE 'ref-[a-z-]+' | head -1)
  dr=$(pgrep -af 'docker run' 2>/dev/null | grep -oE 'ref-[a-z-]+' | head -1)
  echo "active: repo[${active:-none}]  codex[${cx:-idle}]  build[${db:-none}]  replay[${dr:-none}]"
  echo "---------------------------------------------------------------"
  echo " legend: ########## = stages 0..8   [DONE] full exam   [>>] active   [FAIL] stopped"
  echo "---------------------------------------------------------------"

  ACTIVE="$active" python3 - <<'PY'
import json, os, pathlib
pilot = ["achno-gowall","alexhallam-tv","alexpovel-srgn","afnanenayet-diffsitter","benhoyt-goawk",
         "homeport-dyff","graphql-hive-graphql-inspector","afuh-rick-and-morty-api","anvilco-spectaql",
         "neilotoole-sq","eralchemy-eralchemy","supabase-postgres-meta","activecm-rita-legacy",
         "bee-san-name-that-hash","betterleaks-betterleaks"]
out = pathlib.Path("out"); active = os.environ.get("ACTIVE","")
done = failed = 0
for r in pilot:
    s = out / r / "STATUS.json"
    st = json.loads(s.read_text(encoding="utf-8")) if s.exists() else {}
    passed = sorted(int(k) for k, v in st.items() if v == "pass")
    hi = passed[-1] if passed else -1
    failst = [k for k, v in st.items() if v != "pass"]
    tdir = out / r / "05_tests"
    nt = sum(1 for _ in tdir.rglob("*.json")) if tdir.exists() else 0
    if st.get("8") == "pass":
        icon, done = "[DONE]", done + 1
    elif r == active:
        icon = "[>> ]"
    elif failst:
        icon, failed = "[FAIL]", failed + 1
    else:
        icon = "[   ]" if not passed else "[ . ]"
    bar = "".join("#" if i <= hi else "." for i in range(9))
    note = ""
    if st.get("8") != "pass" and failst:
        note = f"  stage{failst[0]} stopped"
    elif nt:
        note = f"  {nt} tests"
    print(f" {icon} {r:32s} {bar} s{hi if hi>=0 else '-'}{note}")
print("---------------------------------------------------------------")
print(f" full exams: {done}/15      stopped/queued: {failed}")
PY
  LOG=$(ls -t scripts/rerun*.log 2>/dev/null | head -1)
  echo "--- recent orchestrator log (${LOG##*/}) ---"
  tail -4 "$LOG" 2>/dev/null | cut -c1-63 | sed 's/^/  /'
  echo "(refresh every ${INTERVAL}s  -  Ctrl-C to quit)"
  sleep "$INTERVAL"
done
