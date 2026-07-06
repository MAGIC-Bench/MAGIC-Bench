#!/usr/bin/env bash
# 把服务器上的 golden/卷面/候选提交/成绩 备份到本机。在本机 Git Bash 跑(隧道开着即可):
#   bash /d/code-bench-v2/backup_to_local.sh
# 想定时备份: Windows 任务计划 调用 "C:\Program Files\Git\bin\bash.exe" D:/code-bench-v2/backup_to_local.sh
set -u
DST="${DST:-/d/code-bench-v2/backup}"
mkdir -p "$DST"
SSH="ssh -i $HOME/.ssh/id_rsa -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p 2222 root@127.0.0.1"
ts() { date '+%H:%M:%S'; }

echo "[$(ts)] 备份 golden+卷面 (out/*/07_exam) ..."
$SSH "cd /mnt/yangh559/code-bench-v2 && tar czf - out/*/07_exam 2>/dev/null" | tar xzf - -C "$DST" 2>/dev/null \
  && echo "  ok" || echo "  (空或失败)"

echo "[$(ts)] 备份 成绩+提交(去构建产物)+考卷 ..."
# 排除所有 build.sh 能重建的构建产物/依赖缓存(否则几十 GB)。含 Go 的 .gomodcache/.gocache、Rust 的 target/.cargo、
# JS 的 node_modules、Python 的 .venv 等;只留源码+build.sh+run.json。
EXC="--exclude=node_modules --exclude=target --exclude=.venv --exclude=venv --exclude=dist --exclude=build \
--exclude=.git --exclude=__pycache__ --exclude=.gomodcache --exclude=.gocache --exclude=gocache --exclude=gomodcache \
--exclude=.cargo --exclude=.cache --exclude=.npm --exclude=.pytest_cache --exclude=vendor --exclude='*.lock' \
--exclude=.rustup --exclude=.gopath --exclude=_ref --exclude=.gradle --exclude=.m2 --exclude=.stack-work \
--exclude=phpcs-vendor --exclude=flatcc-src --exclude=flatcc_bin --exclude='*.rlib' --exclude='*.rmeta' \
--exclude='.ref-*' --exclude='ref-*' --exclude=.next --exclude=.nuxt --exclude=.svelte-kit --exclude=coverage \
--exclude=.tox --exclude=.mypy_cache --exclude=.ruff_cache --exclude=.deno --exclude=_build --exclude=obj \
--exclude='.rustup*' --exclude='.cargo*' --exclude='.go' --exclude='.gohome' --exclude='gopath' --exclude='.gocache*'"
# 注意 \$EXC 必须本地展开($EXC 而非 \$EXC),否则在远端展开=空=啥都不排(踩过这个坑,备份暴涨到几十G)
$SSH "cd /mnt/yangh559 && tar czf - $EXC chuti-run/grades chuti-run/submissions chuti-run/exams 2>/dev/null" | tar xzf - -C "$DST" 2>/dev/null \
  && echo "  ok" || echo "  (空或失败)"

echo "[$(ts)] 备份完成 -> $DST"
du -sh "$DST" 2>/dev/null
