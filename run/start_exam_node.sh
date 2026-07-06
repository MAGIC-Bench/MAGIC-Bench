#!/usr/bin/env bash
# 做题节点(node6~20)启动器 —— 按主机名尾号自动定 agent 类型,持续轮询考卷队列做题。
# 在【每个做题节点】网页终端粘同一句即可:
#   bash /mnt/yangh559/code-bench-v2/run/start_exam_node.sh
# 映射(每类3台):  node6-8=claude  node9-11=codex  node12-14=cursor  node15-17=kimi  node18-20=agy
# 手动指定也行:    AGENT=claude bash /mnt/yangh559/code-bench-v2/run/start_exam_node.sh
set -u
PREFIX=/mnt/yangh559; CODE=$PREFIX/code-bench-v2
source "$PREFIX/bench/env_profile.sh" >/dev/null 2>&1
host=$(hostname)

if [ -z "${AGENT:-}" ]; then
  n=$(echo "$host" | grep -oE '[0-9]+$')
  types=(claude codex cursor kimi agy)
  if [ -n "$n" ] && [ "$n" -ge 6 ] && [ "$n" -le 20 ]; then
    AGENT=${types[$(( (n - 6) / 3 ))]}
  else
    echo "无法从主机名 '$host' 推断 agent(尾号需 6~20);手动: AGENT=<claude|codex|cursor|kimi|agy> bash $0"
    exit 1
  fi
fi
echo "做题节点 $host  ->  agent = $AGENT"
bin="$AGENT"; [ "$AGENT" = cursor ] && bin=cursor-agent   # 类型 cursor -> 二进制 cursor-agent
command -v "$bin" >/dev/null 2>&1 || { echo "✗ agent '$AGENT' (二进制 $bin) 不在 PATH(先确认已登录/装好)"; exit 4; }
if pgrep -f exam_worker.sh >/dev/null 2>&1; then echo "本节点已有做题 worker 在跑,跳过(防重复)"; exit 0; fi

# 隔离基建:建非 root 用户 examinee + 种各 agent 鉴权(无记忆)+ 锁 golden(out/ 700)。幂等。
bash "$CODE/run/setup_examinee.sh" || echo "⚠ examinee 基建失败;worker 会自检并按 EXAM_NONROOT 处理"

mkdir -p "$PREFIX/chuti-run/logs"
AGENT="$AGENT" nohup bash "$CODE/run/poll.sh" 25 bash "$CODE/run/exam_worker.sh" \
  > "$PREFIX/chuti-run/logs/exam-$host.log" 2>&1 &
echo "做题 worker 已起 (agent=$AGENT) pid $!  —— 持续轮询 exams/ 队列,认领→做题→提交"
