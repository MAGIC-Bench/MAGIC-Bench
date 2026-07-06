#!/usr/bin/env bash
# 出题实时监听 —— 在任意节点(或 netnode)的终端跑,每 N 秒刷新整条出题流水线进度。
#   bash monitor.sh [manifest] [刷新秒数]
# 默认看全量 121。Ctrl-C 退出。
set -u
CODE=/mnt/yangh559/code-bench-v2
MAN=${1:-$CODE/dataset/repo-list.manifest.json}
INT=${2:-5}
trap 'echo; echo 退出监听; exit 0' INT
while true; do
  clear 2>/dev/null || printf '\033[2J\033[H'
  echo "════════ 出题实时监听  $(date '+%F %T')  ════════"
  python3 "$CODE/run/monitor.py" "$MAN"
  echo
  echo "(每 ${INT}s 刷新 · Ctrl-C 退出 · 清单 $(basename "$MAN"))"
  sleep "$INT"
done
