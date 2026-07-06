#!/usr/bin/env bash
echo "=== memory now ==="
free -h
echo "=== OOM killer / killed process in kernel log ==="
dmesg 2>/dev/null | grep -iE 'out of memory|oom-kill|killed process|oom_reaper' | tail -8 || echo "  (dmesg unavailable without sudo)"
echo "=== orphaned build procs (parent pid = 1 means orphaned) ==="
for p in $(pgrep -E 'cargo|pnpm|yarn' 2>/dev/null); do
  ppid=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
  echo "  pid=$p ppid=$ppid $(ps -o comm= -p "$p" 2>/dev/null)"
done | head
echo "=== docker images now (any new ref- built?) ==="
docker images --format '{{.Repository}}' 2>/dev/null | grep '^ref-' | sort
