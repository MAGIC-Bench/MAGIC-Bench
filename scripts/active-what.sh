#!/usr/bin/env bash
echo "=== active codex: which repo (cwd) + stage ==="
for pid in $(pgrep -f 'codex exec' 2>/dev/null); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null)
  stg=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -oE 'STAGE [0-9]+|stage5|drafts' | head -1)
  [ -n "$cwd" ] && echo "  pid=$pid  $(basename "$cwd")  ${stg:-?}"
done
echo "=== active docker run: which image ==="
for pid in $(pgrep -f 'docker run' 2>/dev/null); do
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -oE 'ref-[a-z-]+' | head -1 | sed 's/^/  /'
done
echo "=== did any repo status change in last check? ==="
for id in neilotoole-sq afuh-rick-and-morty-api supabase-postgres-meta; do
  echo -n "  $id: "; tr -d '\n ' < "/mnt/d/code-bench/out/$id/STATUS.json" 2>/dev/null | grep -oE '"[0-9]":"(pass|fail[^"]*)"' | tr '\n' ' '; echo
done
echo "=== /tmp codebench workdirs (live replay = progress) ==="
ls -d /tmp/codebench_* 2>/dev/null | wc -l
