#!/usr/bin/env bash
# 出卷侧：把一道做完的题(stage0-8)的【去标识考生包】发布到考试队列。
# golden(out/<id>/07_exam/grader)绝不进 exams/——考试节点拿不到答案。
#   bash publish_exam.sh <repo_id>
set -u
PREFIX=/mnt/yangh559
CODE=$PREFIX/code-bench-v2
STATE=$PREFIX/chuti-run
id=${1:?用法: publish_exam.sh <repo_id>}
src=$CODE/out/$id/07_exam/candidate
pkg=$CODE/out/$id/07_exam/package.json
[ -d "$src" ] || { echo "[$id] 无考生包(stage8未完成?) $src"; exit 1; }

dst=$STATE/exams/$id
mkdir -p "$STATE/exams"
# 原子发布:先在同盘临时目录拼好(candidate+meta+READY),再整目录 rename 替换,
# 消费者只会看到完整目录,绝不会撞上半写的考生包(见审查 concurrency 项)。
tmp="$STATE/exams/.$id.tmp.$$"
rm -rf "$tmp"; mkdir -p "$tmp"
cp -r "$src" "$tmp/candidate"                       # 只发考生包,无 grader/golden
gen=$(tr -d "[:space:]" < "$src/generation_language.txt" 2>/dev/null)
scen=$(python3 -c "import json;print(json.load(open('$CODE/out/$id/07_exam/grader/_grader_meta.json')).get('scenario_type','cli'))" 2>/dev/null || echo cli)
printf '{"id":"%s","scenario_type":"%s","generation_language":"%s"}\n' "$id" "${scen:-cli}" "${gen:-unknown}" > "$tmp/meta.json"
touch "$tmp/READY"
rm -rf "$dst"; mv -T "$tmp" "$dst" 2>/dev/null || { rm -rf "$dst" "$tmp"; cp -r "$src" "$dst/candidate" 2>/dev/null; }
echo "[$id] 已发布到考试队列 ($dst) gen=${gen:-unknown} scen=${scen:-cli}"
