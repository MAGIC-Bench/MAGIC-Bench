#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
now=$(date +%s)
echo "=== daemon alive? ==="
pgrep -af 'run_dataset.py' | grep -v pgrep | cut -c1-70 || echo "  DEAD"
echo "=== full rerun3.log ==="
cat scripts/rerun3.log 2>/dev/null
echo "=== active right now ==="
pgrep -afl 'codex exec|docker build|docker run|cargo|pnpm|yarn|go build' 2>/dev/null | grep -v pgrep | grep -oiE 'codex exec|docker build|docker run|cargo|pnpm|yarn|go build' | sort | uniq -c
echo "=== diffsitter: building how long? ==="
df="repos/afnanenayet-diffsitter/Dockerfile.codebench"
[ -f "$df" ] && echo "  Dockerfile age: $(( now - $(stat -c%Y "$df") ))s"
echo "  STATUS: $(tr -d '\n ' < out/afnanenayet-diffsitter/STATUS.json 2>/dev/null)"
echo "=== the 7 rerun repos: current stage ==="
for id in afnanenayet-diffsitter graphql-hive-graphql-inspector afuh-rick-and-morty-api anvilco-spectaql neilotoole-sq supabase-postgres-meta activecm-rita-legacy; do
  echo "  $id: $(tr -d '\n ' < out/$id/STATUS.json 2>/dev/null | grep -oE '"[0-9]":"(pass|fail)[^"]*"' | tr '\n' ' ')"
done
