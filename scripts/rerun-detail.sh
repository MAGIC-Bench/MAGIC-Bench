#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
now=$(date +%s)
echo "=== build-failure repos: Dockerfile regenerated? + STATUS age ==="
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector; do
  df="repos/$id/Dockerfile.codebench"; st="out/$id/STATUS.json"
  if [ -f "$df" ]; then dfs="DF:regenerated($(( (now-$(stat -c%Y "$df")) ))s ago)"; else dfs="DF:MISSING(awaiting codex)"; fi
  if [ -f "$st" ]; then sts="STATUS:$(( (now-$(stat -c%Y "$st")) ))s ago"; else sts="STATUS:none"; fi
  echo "  $id  $dfs  $sts"
done
echo "=== which repos are currently active (cwd of codex procs) ==="
for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null)
  [ -n "$cwd" ] && basename "$cwd"
done | sort | uniq -c
echo "=== docker build processes now ==="
pgrep -af 'docker build|cargo|pnpm|yarn|go build' 2>/dev/null | grep -v pgrep | grep -oE '\-t ref-[a-z-]+|cargo|pnpm|yarn' | head
