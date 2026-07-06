#!/usr/bin/env bash
# 调某个 agent 无头解题:卷面已在 $WORK,agent 在 $WORK 内交付 build.sh + run.json + 源码。
#   agent_adapter.sh <agent> <work_dir> <gen_lang>
# 现状:codex 已验证可用;claude/kimi/cursor/antigravity 已接线但需各自登录后验证。
set -u
AGENT=$1; WORK=$2; GEN=$3
PROMPT="你在参加一场编程考试。当前工作目录就是卷面:prompt.md(任务)+ 中文卷面文档(项目描述/用户API使用手册/功能模块文档/用户行为示例文档/非功能需求)+ 机器可读契约(02_*.json)。
用 ${GEN} 实现这个项目,使其对外可观察行为与卷面契约完全一致。在【本目录】交付:
1) build.sh —— 原生构建你的实现(禁用 docker;联网用国内镜像 pip清华/GOPROXY=goproxy.cn/npm npmmirror/cargo USTC;禁离线/frozen;依赖隔离进本目录;成功 exit 0)。
2) run.json —— {\"launch\":[\"<运行你工具的 argv,绝对路径>\"],\"smoke\":[\"--help\"]}。cli→launch 即你的 CLI;service→launch 启服务监听 \$PORT 并提供健康检查;pipeline→输入路径→输出路径。
3) 你的源码。
【只能读写本目录,严禁访问本目录以外的任何文件/路径】。最后自己跑一遍 build.sh 确认能构建。只输出你写了哪些文件。"

# 进度感知看门狗(给网络不稳的 cursor/agy 用):后台跑 agent,只在【长时间无任何文件写入=真卡死/断流】
# 或【超硬上限】时才杀,正在写文件(有进展)就不动它 → 不误杀"慢但有效"的连接。
run_watch() {
  ( cd "$WORK" && "$@" ) &
  local pid=$! stall=${FLAKY_STALL:-240} maxt=${FLAKY_MAX:-1500}
  local start last now sig prev; start=$(date +%s); last=$start; prev=""
  while kill -0 "$pid" 2>/dev/null; do
    sleep 20
    [ -f "$WORK/build.sh" ] && break                          # 出活了,让它自然收尾
    sig=$(find "$WORK" -type f -printf '%s.%T@ ' 2>/dev/null | md5sum | cut -c1-16)
    now=$(date +%s)
    [ "$sig" != "$prev" ] && { prev="$sig"; last=$now; }       # 文件有变动=有进展,刷新计时
    if [ $((now-last)) -ge "$stall" ] || [ $((now-start)) -ge "$maxt" ]; then
      kill -TERM "$pid" 2>/dev/null; sleep 5; kill -KILL "$pid" 2>/dev/null; break
    fi
  done
  wait "$pid" 2>/dev/null
}

case "$AGENT" in
  codex)                                   # 已验证
    codex exec "$PROMPT" --cd "$WORK" --sandbox danger-full-access \
      --skip-git-repo-check --color never -c model_reasoning_effort=high </dev/null ;;
  claude)                                  # Opus 4.8(账号默认)+ 思考深度 medium(从 high 降档省额度)
    ( cd "$WORK" && claude -p "$PROMPT" --add-dir "$WORK" --effort medium \
        --allowedTools Read Write Edit Bash Grep Glob --permission-mode acceptEdits </dev/null ) ;;
  kimi)                                    # kimi-for-coding;-p 本就非交互,不能再叠 --auto/--yolo(会报冲突)
    ( cd "$WORK" && kimi -p "$PROMPT" </dev/null ) ;;
  cursor)                                  # 网络不稳:进度感知看门狗(卡死/断流才杀,有进展不动)→ 新进程重试
    for i in $(seq 1 "${FLAKY_RETRY:-4}"); do
      run_watch cursor-agent -p "$PROMPT" --force ${CURSOR_API_KEY:+--api-key "$CURSOR_API_KEY"} </dev/null
      [ -f "$WORK/build.sh" ] && break
      echo "[adapter] cursor 第 $i 次没出 build.sh(卡死/断流),换新进程重试"
    done ;;
  antigravity|agy)                         # 同上;Gemini 3.1 Pro(High)
    for i in $(seq 1 "${FLAKY_RETRY:-4}"); do
      run_watch agy -p "$PROMPT" --add-dir "$WORK" --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions </dev/null
      [ -f "$WORK/build.sh" ] && break
      echo "[adapter] agy 第 $i 次没出 build.sh(超时/断流),换新进程重试"
    done ;;
  *) echo "未知 agent: $AGENT"; exit 6 ;;
esac
