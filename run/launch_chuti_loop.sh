#!/usr/bin/env bash
# 出题【自愈循环】—— 反复跑 launch_chuti,直到全部完成。
# 每轮先清掉"限流/中途截断"类【可重试】失败(真失败/原仓难做基准的保留),自动跨越 Claude 限流窗口:
# 本轮无进展(多半是额度耗尽)就睡一阵等 reset,再来。在出题节点跑:
#   source env_profile.sh && nohup bash run/launch_chuti_loop.sh > /mnt/yangh559/chuti-run/logs/loop-$(hostname).log 2>&1 &
set -u
PREFIX=/mnt/yangh559; CODE=$PREFIX/code-bench-v2; ST=$PREFIX/chuti-run
MAN=${MANIFEST:-$CODE/dataset/repo-list.manifest.json}
total=$(python3 -c "import json;print(len(json.load(open('$MAN'))['repos']))" 2>/dev/null || echo 121)
ts(){ date -u +%H:%M:%S; }
idle_sleep=${IDLE_SLEEP:-1200}      # 全限流时睡多久等额度恢复(默认 20 分钟)

while true; do
  cleared=0
  for f in "$ST"/failed/*; do
    [ -e "$f" ] || continue
    id=$(basename "$f"); log="$ST/logs/$id.log"
    # 限流 / 中途截断("did not write" 在限流时也会出现)→ 可重试;原仓自测不过 / no surviving 不重试
    if grep -qiE "额度|限流|usage limit|rate.?limit|429|did not write" "$log" 2>/dev/null \
       && ! grep -qiE "no surviving|bad golden" "$log" 2>/dev/null; then
      rm -f "$f"; cleared=$((cleared+1))
    fi
  done
  done_n=$(ls "$ST"/done 2>/dev/null | wc -l)
  echo "[$(ts)] 自愈轮: 完成 $done_n/$total | 本轮清掉可重试失败 $cleared"
  [ "$done_n" -ge "$total" ] && { echo "[$(ts)] ✅ 全部完成 $done_n/$total"; break; }

  before=$done_n
  bash "$CODE/run/launch_chuti.sh"
  after=$(ls "$ST"/done 2>/dev/null | wc -l)

  if [ "$after" -le "$before" ]; then
    # 本轮没新完成:若也没东西可清,基本是额度耗尽 → 睡久点等 reset;否则短睡再试
    if [ "$cleared" -eq 0 ]; then
      echo "[$(ts)] 本轮 0 进展且无可重试 → 睡 ${idle_sleep}s 等 Claude 额度恢复"
      sleep "$idle_sleep"
    else
      echo "[$(ts)] 本轮清了失败但没新完成 → 睡 600s 再试"
      sleep 600
    fi
  fi
done
