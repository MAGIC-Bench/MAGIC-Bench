#!/usr/bin/env bash
cd /mnt/d/code-bench/out || exit 9
for r in benhoyt-goawk betterleaks-betterleaks alexpovel-srgn bee-san-name-that-hash eralchemy-eralchemy homeport-dyff; do
  echo "===== $r/07_exam ====="
  find "$r/07_exam" -type f 2>/dev/null | sort
  echo "  cases: $(ls "$r/07_exam/grader/cases" 2>/dev/null | wc -l) json"
  echo
done
