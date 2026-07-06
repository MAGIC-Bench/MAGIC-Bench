#!/usr/bin/env bash
# 考试节点 worker —— 在每个考试节点上跑,AGENT=该节点的 agent 类型。
#   AGENT=codex source env_profile.sh && bash exam_worker.sh
# 多节点同类型并发安全:对每道 ready 题原子认领 (题×类型),一道题每类只 1 个节点考。
# 隔离(已实测可用):agent 以非 root 用户 examinee 跑 + golden 目录 chmod700 → examinee 读不到 golden
# (NFS sec=sys 无 root_squash);每场考试全新 HOME(仅鉴权,无历史)→ 无跨场记忆污染。
set -u
umask 022                                                  # 否则容器默认 umask 077 → 中间目录 700,examinee 无法 traverse 进自己的 workdir/HOME
PREFIX=/mnt/yangh559
CODE=$PREFIX/code-bench-v2
STATE=$PREFIX/chuti-run
EXAMS=$STATE/exams
ECLAIM=$STATE/exam_claims; EDONE=$STATE/exam_done; SUBS=$STATE/submissions
LOGS=$STATE/logs
AGENT=${AGENT:?需指定 AGENT=codex|claude|kimi|cursor|antigravity}
NODE=$(hostname)
WORKROOT=${EXAM_WORKROOT:-/tmp/exam_work}                  # 容器本地、examinee 可达(不在 /root,不在 /mnt)
NONROOT=${EXAM_NONROOT:-1}                                 # 1=以 examinee 跑(硬隔离);0=回退 root(无隔离)
TPL=/home/examinee/.authtpl
mkdir -p "$ECLAIM" "$EDONE" "$SUBS" "$LOGS" "$WORKROOT"
ts(){ date -u +%H:%M:%S; }
_bin="$AGENT"; [ "$AGENT" = cursor ] && _bin=cursor-agent   # 类型 cursor -> 二进制 cursor-agent
command -v "$_bin" >/dev/null 2>&1 || { echo "agent '$AGENT' (二进制 $_bin) 不在 PATH"; exit 4; }

# 隔离基建:确保 examinee + 鉴权模板 + golden 锁就绪(幂等)。
if [ "$NONROOT" = 1 ]; then
  # 重建条件:examinee 不存在 / 模板缺失 / 或 claude 凭证还是【冻结副本(普通文件,非软链)】= 老模板 → 重建升级到实时 token
  if ! id examinee >/dev/null 2>&1 || [ ! -d "$TPL" ] \
     || { [ -e "$TPL/.claude/.credentials.json" ] && [ ! -L "$TPL/.claude/.credentials.json" ]; }; then
    bash "$CODE/run/setup_examinee.sh" || { echo "examinee 基建失败"; exit 8; }
  fi
  # 自检:examinee 必须读不到 golden,否则隔离没生效
  if runuser -u examinee -- bash -c "ls $CODE/out >/dev/null 2>&1"; then
    echo "[警告] examinee 仍能进 out/ —— golden 未锁;重锁中"; chmod 700 "$CODE/out" 2>/dev/null
    runuser -u examinee -- bash -c "ls $CODE/out >/dev/null 2>&1" \
      && { echo "仍未隔离,拒绝(设 EXAM_NONROOT=0 可强制无隔离跑)"; exit 7; }
  fi
fi

# 以 examinee(或 root 回退)跑一个命令:全新 HOME=仅鉴权模板的副本,无记忆。
run_as() {  # run_as <home_dir> -- <cmd...>
  local home="$1"; shift; [ "$1" = -- ] && shift
  if [ "$NONROOT" = 1 ]; then
    runuser -m -u examinee -- env HOME="$home" "$@"        # -m 保留 PATH/代理等;HOME 改到全新鉴权目录
  else
    env HOME="$home" "$@"
  fi
}

took=0
shopt -s nullglob
for ready in "$EXAMS"/*/READY; do
  [ -e "$STATE/STOP" ] && break
  id=$(basename "$(dirname "$ready")")
  [ -e "$EDONE/$id/$AGENT" ] && continue                   # 我这类已考过
  mkdir -p "$ECLAIM/$id"
  mkdir "$ECLAIM/$id/$AGENT" 2>/dev/null || continue       # 原子认领 (题×类型);被同类别的节点抢了则跳过
  echo "$NODE start=$(date -u +%FT%TZ)" > "$ECLAIM/$id/$AGENT/owner"
  echo "[$(ts)] $NODE($AGENT) ▶ 认领考试 $id" | tee -a "$LOGS/exam-$NODE.log"

  work="$WORKROOT/$AGENT/$id"
  rm -rf "$work"; mkdir -p "$work"
  cp -r "$EXAMS/$id/candidate/." "$work/"                  # 只拷考生包(去标识,无 golden)
  gen=$(python3 -c "import json;print(json.load(open(\"$EXAMS/$id/meta.json\")).get(\"generation_language\",\"unknown\"))" 2>/dev/null || echo unknown)
  eh="$WORKROOT/.home/$AGENT/$id"; rm -rf "$eh"; mkdir -p "$eh"   # 全新 HOME(每场一份鉴权,无记忆)
  if [ "$NONROOT" = 1 ]; then
    cp -a "$TPL/." "$eh/" 2>/dev/null
    chown -R examinee:examinee "$work" "$eh"
    chmod -R u+rwX "$work" "$eh"                            # examinee 对自己 workdir/HOME 内一切可写(模板/考生包里可能有只读目录 → 否则 agent mkdir EACCES)
    # 中间目录设可 traverse(755),否则 examinee 进不去自己的 leaf 目录 → EACCES
    chmod 755 "$WORKROOT" "$WORKROOT/$AGENT" "$WORKROOT/.home" "$WORKROOT/.home/$AGENT" 2>/dev/null
  fi

  if run_as "$eh" -- bash "$CODE/run/agent_adapter.sh" "$AGENT" "$work" "$gen" >"$LOGS/exam-$id-$AGENT.log" 2>&1 \
       && [ -f "$work/build.sh" ]; then
    dst="$SUBS/$id/$AGENT"; rm -rf "$dst"; mkdir -p "$dst"
    cp -r "$work/." "$dst/work/"                           # 候选仓回传持久盘(root 可读 examinee 文件)
    touch "$dst/SUBMITTED"; mkdir -p "$EDONE/$id"; touch "$EDONE/$id/$AGENT"
    took=$((took+1))
    echo "[$(ts)] $NODE($AGENT) ✔ 提交 $id" | tee -a "$LOGS/exam-$NODE.log"
  else
    echo "[$(ts)] $NODE($AGENT) ✗ 考试失败 $id(见 exam-$id-$AGENT.log);释放认领" | tee -a "$LOGS/exam-$NODE.log"
    rm -rf "$ECLAIM/$id/$AGENT"                            # 释放,留给同类其它节点/重跑
  fi
  rm -rf "$work" "$eh"                                     # 清场:不留候选残留/记忆
done
echo "[$(ts)] $NODE($AGENT) 扫描完毕,本节点考了 $took 道"
