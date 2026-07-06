#!/usr/bin/env bash
# 防抖动 / 续跑看门狗:回收"已认领但久未产出"的任务,使掉线/中断的考试与出题被自动重新拾起。
#   poll.sh 60 bash reap_stale.sh   (在 node1 周期跑即可,认领都在共享 /mnt)
# 语义:
#   出题侧 —— 流水线分阶段,产物落 out/<id>;释放认领后下一轮从已有产物处续跑(部分续跑)。
#   做题侧 —— agent 无状态,释放认领后由同类节点重新【整场重考】(无法断点续,fresh 重做)。
set -u
STATE=/mnt/yangh559/chuti-run
TIMEOUT=${REAP_TIMEOUT:-2400}        # 秒:认领超过此时长仍无产出 → 判定掉线,释放(默认 40 分钟,够最慢的仓跑完)
now=$(date +%s)
ts(){ date -u +%H:%M:%S; }
reaped=0

# 做题:exam_claims/<id>/<agent> 既无 SUBMITTED 也无 exam_done 且超时 → 释放
shopt -s nullglob
for c in "$STATE"/exam_claims/*/*; do
  [ -d "$c" ] || continue
  id=$(basename "$(dirname "$c")"); ag=$(basename "$c")
  [ -e "$STATE/submissions/$id/$ag/SUBMITTED" ] && continue
  [ -e "$STATE/exam_done/$id/$ag" ] && continue
  age=$(( now - $(stat -c %Y "$c" 2>/dev/null || echo "$now") ))
  if [ "$age" -gt "$TIMEOUT" ]; then
    rm -rf "$c"; reaped=$((reaped+1))
    echo "[$(ts)] [reap] 释放掉线考试认领 $id/$ag age=${age}s → 留待重考"
  fi
done

# 出题:claims/<id> 既无 done 也无 failed 且超时 → 释放(续跑)
for c in "$STATE"/claims/*; do
  [ -d "$c" ] || continue
  id=$(basename "$c")
  [ -e "$STATE/done/$id" ] && continue
  [ -e "$STATE/failed/$id" ] && continue
  age=$(( now - $(stat -c %Y "$c" 2>/dev/null || echo "$now") ))
  if [ "$age" -gt "$TIMEOUT" ]; then
    rm -rf "$c"; reaped=$((reaped+1))
    echo "[$(ts)] [reap] 释放掉线出题认领 $id age=${age}s → 续跑"
  fi
done
# 判卷:grade_claims/<id>/<type> 无 GRADED 且超时 → 释放(判卷节点掉线/判挂了 → 由别的判卷节点重判)
for c in "$STATE"/grade_claims/*/*; do
  [ -d "$c" ] || continue
  id=$(basename "$(dirname "$c")"); ty=$(basename "$c")
  [ -e "$STATE/grades/$id/$ty/GRADED" ] && continue
  age=$(( now - $(stat -c %Y "$c" 2>/dev/null || echo "$now") ))
  if [ "$age" -gt "$TIMEOUT" ]; then
    rm -rf "$c"; reaped=$((reaped+1))
    echo "[$(ts)] [reap] 释放掉线判卷认领 $id/$ty age=${age}s → 留待重判"
  fi
done

[ "$reaped" -gt 0 ] && echo "[$(ts)] [reap] 本轮回收 $reaped 个掉线认领"
exit 0
