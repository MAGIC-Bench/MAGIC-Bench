#!/usr/bin/env bash
# 循环跑某 worker,直到出现 /mnt/yangh559/chuti-run/STOP。用于持续运营(出卷边产、考试/判卷边消费)。
#   [AGENT=codex] bash poll.sh <interval_sec> <worker-cmd...>
set -u
STOP=/mnt/yangh559/chuti-run/STOP
n=${1:?用法: poll.sh <秒> <命令...>}; shift
while [ ! -e "$STOP" ]; do
  "$@" || true
  [ -e "$STOP" ] && break
  sleep "$n"
done
echo "[poll] 检测到 STOP,退出"
