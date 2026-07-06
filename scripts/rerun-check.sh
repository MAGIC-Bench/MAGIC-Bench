#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== codex calls running now (stage + effort) ==="
pgrep -af 'codex exec' | grep -oE 'STAGE [0-9]+|reasoning_effort=[a-z]+' | sort | uniq -c
echo "=== run_dataset alive? ==="
pgrep -af 'run_dataset' | grep -v pgrep | grep -oE '\-\-jobs [0-9]+ --only' | head -1 || echo "  (not running)"
echo "=== build-failure Dockerfiles (deleted -> codex regenerating) ==="
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector; do
  if [ -f "repos/$id/Dockerfile.codebench" ]; then echo "  $id: regenerated"; else echo "  $id: (awaiting codex)"; fi
done
echo "=== current STATUS of the 9 ==="
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector afuh-rick-and-morty-api supabase-postgres-meta neilotoole-sq; do
  echo -n "  $id: "; tr -d '\n ' < "out/$id/STATUS.json" 2>/dev/null; echo
done
