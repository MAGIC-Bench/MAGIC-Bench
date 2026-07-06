#!/usr/bin/env bash
# netnode 总控台:看板 / 一键拉起所有 worker / 停所有 / 成绩矩阵。
#   bash coordinator.sh                看板
#   bash coordinator.sh --launch-all   SSH 拉起所有节点 worker(读 roles.env;持续轮询)
#   bash coordinator.sh --stop-all     置 STOP + 停所有节点 worker
#   bash coordinator.sh --scoreboard   成绩矩阵(题 × agent)
set -u
PREFIX=/mnt/yangh559; CODE=$PREFIX/code-bench-v2; STATE=$PREFIX/chuti-run; RUN=$CODE/run
mkdir -p "$STATE/logs"
[ -f "$RUN/roles.env" ] && source "$RUN/roles.env"
SSH="ssh -i $HOME/.ssh/id_rsa -o StrictHostKeyChecking=no -o ConnectTimeout=8"
ENVP="source /mnt/yangh559/bench/env_profile.sh >/dev/null 2>&1"
POLL=${POLL:-25}

dash(){
  local total done fail ready subs grades
  total=$(python3 -c "import json;print(len(json.load(open(\"$CODE/dataset/repo-list.manifest.json\"))[\"repos\"]))" 2>/dev/null||echo '?')
  done=$(ls "$STATE/done" 2>/dev/null|wc -l); fail=$(ls "$STATE/failed" 2>/dev/null|wc -l)
  ready=$(ls -d "$STATE"/exams/*/READY 2>/dev/null|wc -l)
  subs=$(ls "$STATE"/submissions/*/*/SUBMITTED 2>/dev/null|wc -l)
  grades=$(ls "$STATE"/grades/*/*/GRADED 2>/dev/null|wc -l)
  echo "═══ 流水线看板 ═══"
  echo "出卷:  完成 $done/$total | 失败 $fail | 进行中 $(ls "$STATE/claims" 2>/dev/null|wc -l)"
  echo "考卷:  已发布 $ready"
  echo "考试:  提交 $subs"
  echo "判卷:  完成 $grades"
}

launch_node(){ # host  envline  cmd
  $SSH "$1" "$ENVP; cd $CODE; $2 nohup bash run/poll.sh $POLL $3 >/mnt/yangh559/chuti-run/logs/poll-\$(hostname)-${4:-w}.log 2>&1 &" \
    && echo "  ✔ $1  ($2$3)" || echo "  ✗ $1  SSH 失败"
}

case "${1:-}" in
  --launch-all)
    rm -f "$STATE/STOP"
    echo "拉起出卷节点:"; for h in ${CHUTI_NODES:-}; do launch_node "$h" "" "bash run/launch_chuti.sh" chuti; done
    echo "拉起考试节点:"
    for t in codex claude kimi cursor antigravity; do
      eval "hosts=\${EXAM_NODES_$t:-}"
      for h in $hosts; do launch_node "$h" "AGENT=$t" "bash run/exam_worker.sh" "exam-$t"; done
    done
    echo "拉起判卷节点:"; for h in ${GRADE_NODES:-}; do launch_node "$h" "" "bash run/grade_worker.sh" grade; done ;;
  --stop-all)
    touch "$STATE/STOP"; echo "已置 STOP。停各节点 worker:"
    allh="${CHUTI_NODES:-} ${GRADE_NODES:-}"
    for t in codex claude kimi cursor antigravity; do eval "allh=\"\$allh \${EXAM_NODES_$t:-}\""; done
    for h in $(echo "$allh"|tr ' ' '\n'|sort -u); do
      [ -n "$h" ] && { $SSH "$h" "pkill -f 'poll.sh|launch_chuti.sh|exam_worker.sh|grade_worker.sh'" 2>/dev/null; echo "  停 $h"; }
    done ;;
  --scoreboard) python3 "$RUN/scoreboard.py" ;;
  *) dash ;;
esac
