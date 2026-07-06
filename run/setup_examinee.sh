#!/usr/bin/env bash
# 考试节点隔离基建(start_exam_node 自动调,也可手动跑一次):
#   1) 建非 root 用户 examinee(uid 自动);
#   2) 植入各 agent 的【仅鉴权】配置到模板 .authtpl —— 不含记忆/历史/会话 → 每场考试拷一份全新 HOME,
#      天然无跨场记忆污染;
#   3) 把 golden 根目录 out/ chmod 700 root-only —— NFS sec=sys 无 root_squash,examinee 无法 traverse,
#      读不到任何 golden(已实测 Permission denied);判卷以 root 跑,不受影响。
set -u
U=examinee
SRC=${SRC:-/root}
OUT=/mnt/yangh559/code-bench-v2/out

id "$U" >/dev/null 2>&1 || useradd -m "$U"

TPL=/home/$U/.authtpl
rm -rf "$TPL"; mkdir -p "$TPL/.config"
# codex: auth.json(令牌)+ config.toml(trust_level=trusted 免批准);不拷 sessions/(记忆)
[ -f "$SRC/.codex/auth.json" ] && { mkdir -p "$TPL/.codex"; cp -f "$SRC/.codex/auth.json" "$SRC/.codex/config.toml" "$TPL/.codex/" 2>/dev/null; }
# claude: 只拷 OAuth 凭证;【不拷 .claude.json】(含会话历史/projects)→ 全新无记忆
[ -f "$SRC/.claude/.credentials.json" ] && { mkdir -p "$TPL/.claude"; cp -f "$SRC/.claude/.credentials.json" "$TPL/.claude/" 2>/dev/null; }
# 注意:/root 下 .codex/.claude/.cursor/.gemini/.kimi-code 都是【指向 /mnt agent_state 的软链】。
# 模板里必须放【真实可写副本】(cp -rfL 解引用),否则 examinee 跟着软链去写 root-only 的 /mnt → EACCES。
# kimi: ~/.kimi-code(config.toml 含 token)—— 解引用
[ -e "$SRC/.kimi-code" ] && cp -rfL "$SRC/.kimi-code" "$TPL/" 2>/dev/null
# cursor: 鉴权走 env CURSOR_API_KEY,【不种 .cursor】——种了是指向 /mnt 的软链 examinee 写不了;让它在 HOME 自建
# agy / antigravity: 真正的 OAuth token 在 ~/.gemini/antigravity-cli/antigravity-oauth-token —— 解引用
[ -e "$SRC/.gemini" ] && cp -rfL "$SRC/.gemini" "$TPL/" 2>/dev/null
[ -e "$SRC/.antigravity" ] && cp -rfL "$SRC/.antigravity" "$TPL/" 2>/dev/null
[ -e "$SRC/.config/antigravity" ] && cp -rfL "$SRC/.config/antigravity" "$TPL/.config/" 2>/dev/null

# 兜底:模板里任何残留的指向 /mnt 的软链都换成真实可写副本,并确保 examinee 全可写
find "$TPL" -type l 2>/dev/null | while read -r l; do
  t=$(readlink -f "$l" 2>/dev/null); rm -f "$l"
  [ -n "$t" ] && [ -e "$t" ] && cp -rfL "$t" "$l" 2>/dev/null
done
chown -R "$U:$U" "/home/$U"
chmod -R u+rwX "$TPL" 2>/dev/null

# 注:曾试过把 claude/agy 凭证软链到共享实时态(让大家共用活 token),但【适得其反】——
#   多消费者并发刷新 → 轮换把共享 refresh token 作废 → 一次失败的刷新把"未登录"写回共享文件 → 全体登出。
#   故回退为【冻结副本】(上面 line 20 的 cp):各节点独立,单节点失效不会级联拖垮全部。
#   claude 账号被太多并发消费者拖垮是根因,治本要【减少并发 claude 消费者】或换独立账号,非模板技巧能解。

# 锁 golden:只需把 out/ 顶层置 700 —— examinee 无法 traverse 进入,任何子级 golden 一律读不到。
# root(出题/判卷)无视权限照常读写。幂等。
[ -d "$OUT" ] && chmod 700 "$OUT" 2>/dev/null

echo "[setup_examinee] examinee 就绪;鉴权模板=$TPL;golden 已锁(out/ 700)"
echo -n "[setup_examinee] 自检 examinee 读 golden: "
if [ -d "$OUT" ] && runuser -u "$U" -- bash -c "ls $OUT >/dev/null 2>&1"; then
  echo "可读(异常! 隔离未生效)"
else
  echo "Permission denied(正确,隔离生效)"
fi
