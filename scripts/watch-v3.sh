#!/usr/bin/env bash
# Live dashboard for PILOT v3.  Run in YOUR terminal:
#   wsl bash /mnt/d/code-bench-v2/scripts/watch-v3.sh        (refresh 5s; pass a number to change)
# Ctrl-C to quit. Per-repo stage progress bar (0..8) + the v3 quality signals (argv_drop / open_crit).
cd /mnt/d/code-bench-v2 || exit 9
INTERVAL="${1:-5}"
MAN=dataset/pilot-v3.manifest.json
LOG=scripts/pilot-v3.log
while true; do
  clear
  echo "=============== codegen-bench PILOT v3 monitor ==============="
  printf "time: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')"
  if pgrep -f run_dataset >/dev/null 2>&1; then
    echo "orchestrator: RUNNING ($(pgrep -af run_dataset 2>/dev/null | grep -oE '\-\-jobs [0-9]+' | head -1)) | mem $(free -h | awk 'NR==2{print $7}') free"
  else
    echo "orchestrator: not running   $(grep -h 'repos completed' "$LOG" 2>/dev/null | tail -1)"
  fi
  active=""
  for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
    c=$(readlink "/proc/$pid/cwd" 2>/dev/null); [ -n "$c" ] && active=$(basename "$c")
  done
  cx=$(pgrep -af 'codex exec' 2>/dev/null | grep -oE 'STAGE [0-9]+' | head -1)
  db=$(pgrep -af 'docker build' 2>/dev/null | grep -oE 'ref-[a-z0-9-]+' | head -1)
  echo "active: repo[${active:-none}]  codex[${cx:-idle}]  build[${db:-none}]"
  echo "-------------------------------------------------------------"
  ACTIVE="$active" MAN="$MAN" python3 - <<'PY'
import json, os, pathlib
ids = [r["id"] for r in json.load(open(os.environ["MAN"]))["repos"]]
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
    note = f" stage{fails[0]} stop" if (fails and st.get("8") != "pass") else ""
    sig = ""
    led = out / r / "05_coverage-ledger.json"
    if led.exists():
        try:
            s5 = json.loads(led.read_text(encoding="utf-8"))["summary"]
            sig += f" t={s5.get('tests_emitted')} argv_drop={s5.get('dropped_argv_binary', 0)}"
        except Exception:
            pass
    adv = out / r / "06_adversarial.json"
    if adv.exists():
        try:
            aj = json.loads(adv.read_text(encoding='utf-8'))
            sig += f" open_crit={aj.get('open_critical')}"
            if aj.get('repair_attempts'):
                sig += f" rep={aj.get('repair_attempts')}"
        except Exception:
            pass
    print(f" {icon} {r:26s} {bar} s{hi if hi >= 0 else '-'}{note}{sig}")
print("-------------------------------------------------------------")
print(f" full exams: {done}/{len(ids)}")
PY
  echo "--- recent log ---"
  tail -3 "$LOG" 2>/dev/null | cut -c1-64 | sed 's/^/  /'
  echo "(refresh ${INTERVAL}s  -  Ctrl-C to quit)"
  sleep "$INTERVAL"
done
