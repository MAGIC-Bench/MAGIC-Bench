#!/usr/bin/env bash
# 出卷队列进度 + 维护。任一节点上跑。
#   bash chuti_status.sh                 看进度
#   bash chuti_status.sh --reset-stale   释放所有"进行中"认领（仅在所有节点已停止时用，回收死节点的坑）
#   bash chuti_status.sh --retry-failed  清除失败标记以便重跑
set -u
PREFIX=/mnt/yangh559
CODE=$PREFIX/code-bench-v2
STATE=$PREFIX/chuti-run
MANIFEST=$CODE/dataset/repo-list.manifest.json
total=$(python3 -c "import json;print(len(json.load(open('$MANIFEST'))['repos']))" 2>/dev/null || echo '?')
d=$(ls "$STATE/done" 2>/dev/null | wc -l)
f=$(ls "$STATE/failed" 2>/dev/null | wc -l)
c=$(ls "$STATE/claims" 2>/dev/null | wc -l)
rem='?'; [ "$total" != '?' ] && rem=$(( total - d - f - c ))
echo "出卷进度：完成 $d / $total ｜ 失败 $f ｜ 进行中 $c ｜ 剩余 $rem"
if [ "$f" -gt 0 ]; then echo "── 失败仓："; ls "$STATE/failed" 2>/dev/null | sed 's/^/   /'; fi
if [ "$c" -gt 0 ]; then
  echo "── 进行中（已认领）："
  for x in "$STATE/claims"/*/; do [ -d "$x" ] && echo "   $(basename "$x"): $(cat "$x/owner" 2>/dev/null)"; done
fi
case "${1:-}" in
  --reset-stale)  echo "释放所有进行中认领(出卷+考试+判卷,仅在所有节点已停止时用)…"
                  rm -rf "$STATE/claims"/* "$STATE/exam_claims"/* "$STATE/grade_claims"/* 2>/dev/null
                  echo "完成";;
  --retry-failed) echo "清除失败标记…"; rm -f "$STATE/failed"/* 2>/dev/null; echo "完成";;
esac
