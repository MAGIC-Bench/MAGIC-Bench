#!/usr/bin/env bash
# 在每个节点(node2~5 等)的网页终端跑一次:
#   ① 装控制器公钥 + 开 sshd(让 node1/netnode 以后能内网免密集中调度本节点)
#   ② 起 pilot-10 出题 worker(START_WORKER=0 可只做①不起 worker)
# 用法: bash /mnt/yangh559/code-bench-v2/run/node_init.sh
set -u
PREFIX=/mnt/yangh559; CODE=$PREFIX/code-bench-v2

# ① 控制器公钥 + sshd
mkdir -p /root/.ssh; chmod 700 /root/.ssh
PUB=$PREFIX/bench/conf/id_rsa.pub
if [ -f "$PUB" ]; then
  grep -qF "$(cat "$PUB")" /root/.ssh/authorized_keys 2>/dev/null || cat "$PUB" >> /root/.ssh/authorized_keys
fi
chmod 600 /root/.ssh/authorized_keys 2>/dev/null
ssh-keygen -A >/dev/null 2>&1; mkdir -p /run/sshd
pgrep -x sshd >/dev/null || /usr/sbin/sshd
echo -n "sshd: "; pgrep -x sshd >/dev/null && echo "ON  pod=$(hostname -i)  host=$(hostname)" || echo "FAILED"

# ② 出题 worker —— 用字面量路径:source env_profile 后 $PREFIX 会被改写成 .../bench,不能再用!
if [ "${START_WORKER:-1}" = "1" ]; then
  if pgrep -f launch_chuti.sh >/dev/null 2>&1; then
    echo "本节点已有出题 worker 在跑,跳过(避免重复 OOM)"
  else
    LOGDIR=/mnt/yangh559/chuti-run/logs; mkdir -p "$LOGDIR"
    source /mnt/yangh559/bench/env_profile.sh >/dev/null 2>&1
    cd /mnt/yangh559/code-bench-v2
    MANIFEST=${MANIFEST:-/mnt/yangh559/code-bench-v2/dataset/pilot-10.manifest.json} \
      nohup bash run/launch_chuti.sh >"$LOGDIR/launcher-$(hostname).log" 2>&1 &
    echo "出题 worker 已起 pid $!  ($(hostname))"
  fi
fi
