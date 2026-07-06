#!/usr/bin/env bash
set -u

OUT_DIR="${1:-/mnt/yangh559/chuti-run/rerun_case_metrics}"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

(
  python3 /tmp/rerun_functional_cases.py \
    --agents claude,codex,cursor,kimi \
    --out-dir "$OUT_DIR" \
    --workers 4 \
    --timeout 60 \
    > "$OUT_DIR/run.log" 2>&1
  echo "$?" > "$OUT_DIR/DONE"
) &

echo "$!" > "$OUT_DIR/PID"
echo "started $(cat "$OUT_DIR/PID")"
