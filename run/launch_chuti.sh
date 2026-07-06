#!/usr/bin/env bash
# 出卷工作队列 worker —— 在每个【出卷节点】上跑（多节点并发安全：NFS 原子认领）。
# 用法（每个节点）:
#   source /mnt/yangh559/bench/env_profile.sh && bash /mnt/yangh559/code-bench-v2/run/launch_chuti.sh
# 谁快谁多拿；某节点挂了，它没标 done/failed 的认领可用 chuti_status.sh --reset-stale 释放后重跑。
set -u
PREFIX=/mnt/yangh559
CODE=$PREFIX/code-bench-v2
MANIFEST=${MANIFEST:-$CODE/dataset/repo-list.manifest.json}   # 可用 MANIFEST=... 覆盖(如 pilot-10)
STATE=$PREFIX/chuti-run                      # 队列状态（认领/完成/失败/日志），持久&共享
CLAIMS=$STATE/claims; DONE=$STATE/done; FAILED=$STATE/failed; SKIP=$STATE/skip; LOGS=$STATE/logs
mkdir -p "$CLAIMS" "$DONE" "$FAILED" "$SKIP" "$LOGS"
NODE=$(hostname)
AGENT=${AGENT:-claude}                        # 出题改用 Claude Code(Opus 4.8 medium);codex 仍用于判卷静态分
FROM=${FROM:-0}; TO=${TO:-8}
ts(){ date -u +%H:%M:%S; }

case "$NODE" in *netnode*) echo "拒绝：代理节点不参与出卷"; exit 3;; esac
command -v "$AGENT" >/dev/null 2>&1 || { echo "$AGENT 不在 PATH —— 先 source env_profile.sh"; exit 4; }
[ -f "$MANIFEST" ] || { echo "找不到清单 $MANIFEST"; exit 5; }

mapfile -t REPOS < <(python3 -c "import json;print('\n'.join(r['id'] for r in json.load(open('$MANIFEST'))['repos']))")
echo "[$(ts)] $NODE 上线｜队列 ${#REPOS[@]} 仓｜agent=$AGENT｜stage $FROM..$TO"

did=0
for rid in "${REPOS[@]}"; do
  T=$(cat "$STATE/CHUTI_TARGET_$AGENT" 2>/dev/null || cat "$STATE/CHUTI_TARGET" 2>/dev/null || echo 99999)   # 出题上限(按总完成数);可按 agent 分别设 CHUTI_TARGET_claude / CHUTI_TARGET_codex
  [ "$(ls "$DONE" 2>/dev/null | wc -l)" -ge "$T" ] && { echo "[$(ts)] $NODE 已达出题目标 $T —— 停止出题(省 Claude 额度)" | tee -a "$LOGS/$NODE.log"; break; }
  [ -e "$DONE/$rid" ]   && continue          # 已完成
  [ -e "$SKIP/$rid" ]   && continue          # 永久跳过（golden 不可靠，原仓做不出干净基准）—— 自愈循环也绝不清 skip/
  [ -e "$FAILED/$rid" ] && continue          # 已判失败（删 failed/<id> 可重试）
  mkdir "$CLAIMS/$rid" 2>/dev/null || continue   # 原子认领；被别人认领则跳过
  echo "$NODE pid=$$ start=$(date -u +%FT%TZ)" > "$CLAIMS/$rid/owner"
  echo "[$(ts)] $NODE ▶ 认领 $rid" | tee -a "$LOGS/$NODE.log"
  if python3 "$CODE/run_dataset.py" --manifest "$MANIFEST" --agent "$AGENT" \
        --only "$rid" --from "$FROM" --to "$TO" --jobs 1 >"$LOGS/$rid.log" 2>&1; then
    touch "$DONE/$rid"; did=$((did+1))
    bash "$CODE/run/publish_exam.sh" "$rid" >>"$LOGS/$rid.log" 2>&1 \
      || echo "[$(ts)] $NODE ⚠ publish 失败 $rid" | tee -a "$LOGS/$NODE.log"   # 出完即发布到考试队列
    echo "[$(ts)] $NODE ✔ 完成 $rid" | tee -a "$LOGS/$NODE.log"
  else
    tail -8 "$LOGS/$rid.log" > "$FAILED/$rid" 2>/dev/null || touch "$FAILED/$rid"
    echo "[$(ts)] $NODE ✗ 失败 $rid（见 $LOGS/$rid.log；删 failed/$rid 重试）" | tee -a "$LOGS/$NODE.log"
  fi
  rm -rf "$CLAIMS/$rid"                       # done/failed 标记已防重认，释放认领目录
done
echo "[$(ts)] $NODE 扫描完毕，本节点完成 $did 仓。剩余交由其它节点/重跑处理。"
