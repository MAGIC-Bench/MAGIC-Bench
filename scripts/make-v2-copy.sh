#!/usr/bin/env bash
# Copy the framework (code/prompts/dataset/scripts/docs) into code-bench-v2, excluding the
# huge runtime dirs out/ and repos/ (clones + exam outputs) and .git.
mkdir -p /mnt/d/code-bench-v2
cd /mnt/d/code-bench || exit 9
for x in *; do
  case "$x" in
    out|repos) continue ;;
  esac
  cp -r "$x" /mnt/d/code-bench-v2/ 2>/dev/null
done
echo "=== code-bench-v2 top-level ==="
ls -1 /mnt/d/code-bench-v2
echo "=== sizes ==="
du -sh /mnt/d/code-bench-v2 2>/dev/null
