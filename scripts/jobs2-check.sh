#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 0
pgrep -f run_dataset.py >/dev/null && echo "daemon ALIVE" || echo "DEAD"
echo "concurrent codex (distinct repos):"
for p in $(pgrep -f 'codex exec' 2>/dev/null); do
  c=$(readlink "/proc/$p/cwd" 2>/dev/null); [ -n "$c" ] && basename "$c"
done | sort -u | sed 's/^/  /'
echo "mem:"; free -h | awk 'NR==2{print "  used "$3" / avail "$7" / swap-used "}'; free -h | awk 'NR==3{print "  swap used "$3}'
echo "log tail:"; tail -3 scripts/rerun-v2.log
