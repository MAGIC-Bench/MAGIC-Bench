#!/usr/bin/env bash
# 清节点【本地临时状态】—— 决不触碰持久盘 /mnt/yangh559（依赖/agent/代码/出卷产物都在那）。
# 出卷跑完、或在考生节点换下一题前，在该节点上跑，防状态污染 + 释放容器本地磁盘。
set -u
KEEP=/mnt/yangh559
echo "清理本地临时态（保留 $KEEP）…"
# 临时目录 / 用户缓存
rm -rf /tmp/* /var/tmp/* 2>/dev/null
rm -rf "$HOME/.cache"/* 2>/dev/null
# 包管理缓存
pip cache purge   >/dev/null 2>&1
conda clean -afy  >/dev/null 2>&1
# 工具链本地缓存（非 /mnt）
rm -rf "$HOME/.cargo/registry/cache"/* 2>/dev/null
rm -rf "$HOME/go/pkg/mod/cache/download"/* 2>/dev/null
rm -rf "$HOME/.npm/_cacache"/* 2>/dev/null
# 候选考试残留（若考生在容器本地构建）
rm -rf "$HOME/candidate_work"/* /root/candidate_work/* 2>/dev/null
echo "完成。$KEEP 未触碰。"
echo "── 磁盘 ──"; df -h / "$KEEP" 2>/dev/null | awk 'NR==1||/\/$|mnt/'
