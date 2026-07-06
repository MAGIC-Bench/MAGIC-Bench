#!/usr/bin/env bash
# 判卷 worker —— 在【有 golden】的节点跑(出卷节点或专用判卷节点)。
# 轮询提交,原子认领,构建候选 → 跑 grade.py(内含构建门)→ 写 score.json。
#   source env_profile.sh && bash grade_worker.sh
set -u
PREFIX=/mnt/yangh559
CODE=$PREFIX/code-bench-v2
STATE=$PREFIX/chuti-run
SUBS=$STATE/submissions; GCLAIM=$STATE/grade_claims; GRADES=$STATE/grades; LOGS=$STATE/logs
mkdir -p "$GCLAIM" "$GRADES" "$LOGS"
NODE=$(hostname); ts(){ date -u +%H:%M:%S; }
shopt -s nullglob
graded=0
for sub in "$SUBS"/*/*/SUBMITTED; do
  [ -e "$STATE/STOP" ] && break
  d=$(dirname "$sub"); type=$(basename "$d"); id=$(basename "$(dirname "$d")")
  grep -qw "$type" "$STATE/GRADE_SKIP" 2>/dev/null && continue   # 跳过指定 agent 的判卷(写 chuti-run/GRADE_SKIP,如 agy)
  [ -e "$GRADES/$id/$type/GRADED" ] && continue
  grader="$CODE/out/$id/07_exam/grader"
  [ -d "$grader" ] || continue                            # 此节点没这题的 golden,跳过
  mkdir -p "$GCLAIM/$id"
  mkdir "$GCLAIM/$id/$type" 2>/dev/null || continue       # 原子认领判卷
  out="$GRADES/$id/$type"; mkdir -p "$out"
  log="$LOGS/grade-$id-$type.log"
  work="$d/work"
  echo "[$(ts)] $NODE 判卷 $id/$type" | tee -a "$LOGS/grade-$NODE.log"
  {
    cd "$CODE" 2>/dev/null || cd /tmp                      # 保证有效 cwd:防上一轮 rm 掉的目录残留(getcwd 竞态)致 grade.py 崩
    bash "$work/build.sh" || echo "[build.sh 非零退出 -> grade.py 构建门会判定]"
    launch=$(python3 "$CODE/run/fix_launch.py" "$work" 2>/dev/null)   # 重写做题节点的本地路径 -> 本机 work
    wrap="$work/.candidate_launch.sh"
    printf '#!/usr/bin/env bash\nexec %s "$@"\n' "${launch:-/bin/false}" > "$wrap"; chmod +x "$wrap"
    gtmp=$(mktemp -d)                                     # 每次判卷用独立 grader 副本,避免共享 score.json 竞争
    cp -r "$grader/." "$gtmp/"
    cp -f "$CODE/engine/_grade.py" "$gtmp/grade.py" 2>/dev/null        # 覆盖成最新评分引擎:改动(如静态codex降档)即时对所有卷生效,不必重出
    cp -f "$CODE/engine/nfr_score.py" "$gtmp/nfr_score.py" 2>/dev/null
    cd "$gtmp"
    CANDIDATE_BIN="$wrap" CANDIDATE_SRC="$work" python3 grade.py
    cp "$gtmp/score.json" "$out/score.json" 2>/dev/null
    cd "$CODE" 2>/dev/null; rm -rf "$gtmp"                 # 先 cd 出去再删 gtmp,别把当前 cwd 删了(否则下一轮 getcwd 崩)
  } >"$log" 2>&1
  [ -f "$out/score.json" ] || echo '{"build_ok":false,"功能分":0,"nfr_by_dimension":{}}' > "$out/score.json"
  touch "$out/GRADED"; graded=$((graded+1))
  echo "[$(ts)] $NODE 判完 $id/$type -> $(head -c 140 "$out/score.json")" | tee -a "$LOGS/grade-$NODE.log"
done
echo "[$(ts)] $NODE 本轮判了 $graded 份"
