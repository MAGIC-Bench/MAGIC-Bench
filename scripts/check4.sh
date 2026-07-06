#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== daemon ==="; pgrep -f run_dataset.py >/dev/null && echo ALIVE || echo DEAD
echo "=== the 3 focus repos ==="
for id in afuh-rick-and-morty-api neilotoole-sq supabase-postgres-meta; do
  echo "  $id: $(tr -d '\n ' < out/$id/STATUS.json 2>/dev/null | grep -oE '"[0-9]":"(pass|fail)[^"]*"' | tr '\n' ' ')"
done
echo "=== rerun4.log tail ==="; tail -8 scripts/rerun4.log 2>/dev/null
echo "=== active now ==="
pgrep -afl 'codex exec|docker run|docker build' 2>/dev/null | grep -v pgrep | grep -oiE 'codex exec|docker run|docker build|STAGE [0-9]+' | sort | uniq -c
