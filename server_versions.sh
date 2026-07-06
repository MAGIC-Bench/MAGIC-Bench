#!/usr/bin/env bash
source /mnt/yangh559/bench/env_profile.sh >/dev/null 2>&1 || true
echo "versions"
for c in claude codex kimi cursor-agent agy go rustc cargo node npm python3; do
  printf "%-14s " "$c"
  if command -v "$c" >/dev/null 2>&1; then
    "$c" --version 2>&1 | head -n 1
  else
    echo MISSING
  fi
done
