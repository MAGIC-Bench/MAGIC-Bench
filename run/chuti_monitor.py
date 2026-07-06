#!/usr/bin/env python3
"""出题(生成)进度单帧快照 —— 被本机 watch_chuti.ps1 循环刷新。读 /mnt/yangh559/chuti-run + out/。"""
import glob, os, json, collections

ST = "/mnt/yangh559/chuti-run"
CODE = "/mnt/yangh559/code-bench-v2"
MAN = f"{CODE}/dataset/repo-list.manifest.json"

def base(p): return os.path.basename(p)

total = 0
try:
    total = len(json.load(open(MAN))["repos"])
except Exception:
    total = 0

done = [base(p) for p in glob.glob(f"{ST}/done/*")]
failed = [base(p) for p in glob.glob(f"{ST}/failed/*")]
claims = [base(p) for p in glob.glob(f"{ST}/claims/*")]
published = glob.glob(f"{ST}/exams/*/READY")
pending = total - len(done) - len(failed) - len(claims)

print(f"队列 {total}  |  ✅完成 {len(done)}  |  ❌失败 {len(failed)}  |  ⏳认领中 {len(claims)}  |  待出 {max(pending,0)}  |  📦已发布考卷 {len(published)}")
print("-" * 74)

# 失败原因分类:扫每个失败仓的日志,归因到 stage / 限流 / 其它
reasons = collections.Counter()
ratelimited = []
for f in failed:
    log = f"{ST}/logs/{f}.log"
    txt = ""
    try:
        txt = open(log, errors="replace").read()
    except Exception:
        pass
    low = txt.lower()
    if any(k in low for k in ("额度", "限流", "usage limit", "rate limit", "429", "did not write")):
        # "did not write" 在限流时也会出现(任务被中途截断) -> 归为可重试
        reasons["限流/中途截断(可重试)"] += 1
        ratelimited.append(f)
    elif "no surviving" in low or "bad golden" in low:
        reasons["原仓自测不过/差分不可靠(该仓难做基准)"] += 1
    elif "stage7" in low:
        reasons["stage7 差分用例问题"] += 1
    else:
        reasons["其它(见该仓日志)"] += 1
if failed:
    print("失败归因:")
    for r, c in reasons.most_common():
        print(f"  {c:>4}  {r}")
    print(f"  → 其中【可重试】约 {len(ratelimited)} 个:清 failed/ 后重跑即可(限流恢复后会成功)")
    print("-" * 74)

# 出题节点 launcher 最近一行
print("出题节点最近状态:")
for log in sorted(glob.glob(f"{ST}/logs/launcher-*.log")):
    node = base(log)[9:-4].replace("yangh559-", "")
    try:
        lines = [l for l in open(log, errors="replace").read().splitlines() if l.strip()]
        last = lines[-1][:84] if lines else "(空)"
    except Exception:
        last = "(读不到)"
    running = "🟢" if os.system(f"pgrep -f 'launch_chuti' >/dev/null 2>&1") == 0 else "⚪"
    print(f"  {node:8} {last}")
running = os.popen("pgrep -fc launch_chuti 2>/dev/null").read().strip() or "0"
print(f"\n出题 launcher 在跑的进程数: {running}  (0 = 都跑完一轮退出了,清 failed/ 重跑可续)")
