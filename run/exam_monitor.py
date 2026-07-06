#!/usr/bin/env python3
"""做题/判卷进度单帧快照(被本机 watch_exam.ps1 循环刷新)。读 /mnt/yangh559/chuti-run。"""
import glob, os

ST = "/mnt/yangh559/chuti-run"
AGENTS = ["claude", "codex", "cursor", "kimi", "agy"]

def base(p): return os.path.basename(p)

exams = [base(os.path.dirname(p)) for p in glob.glob(f"{ST}/exams/*/READY")]
graded = glob.glob(f"{ST}/grades/*/*/GRADED")
subs_all = glob.glob(f"{ST}/submissions/*/*/SUBMITTED")
print(f"已发布考卷 {len(exams)}  |  总提交 {len(subs_all)}  |  判完 {len(graded)}")
print("-" * 70)
print(f"{'agent':10}{'认领':>6}{'提交':>6}{'判完':>6}   在做(节点:题)")
for a in AGENTS:
    claimed = glob.glob(f"{ST}/exam_claims/*/{a}")
    subs = glob.glob(f"{ST}/submissions/*/{a}/SUBMITTED")
    gd = glob.glob(f"{ST}/grades/*/{a}/GRADED")
    active = []
    for c in claimed:
        if not os.path.exists(f"{ST}/exam_done/{base(os.path.dirname(c))}/{a}"):
            owner = os.path.join(c, "owner")
            node = open(owner).read().split()[0] if os.path.exists(owner) else "?"
            active.append(f"{node.replace('yangh559-','')}:{base(os.path.dirname(c))[:16]}")
    print(f"{a:10}{len(claimed):>6}{len(subs):>6}{len(gd):>6}   {' '.join(active[:3])}")

print("-" * 70)
print("各做题节点最近一行:")
for log in sorted(glob.glob(f"{ST}/logs/exam-*.log")):
    node = base(log)[5:-4].replace("yangh559-", "")
    try:
        lines = [l for l in open(log, errors="replace").read().splitlines() if l.strip()]
        last = lines[-1][:90] if lines else "(空)"
    except Exception:
        last = "(读不到)"
    print(f"  {node:10} {last}")

# 最近几个分数
print("-" * 70)
print("最近 20 个判出的分:")
import json
sc = sorted(glob.glob(f"{ST}/grades/*/*/score.json"), key=os.path.getmtime, reverse=True)[:20]
for s in sc:
    typ = base(os.path.dirname(s)); rid = base(os.path.dirname(os.path.dirname(s)))
    try:
        d = json.load(open(s))
        f = d.get("功能分", "?"); nfr = d.get("nfr_by_dimension", {})
        ones = sum(1 for dim in nfr.values() for v in dim.values() if v == 1)
        tot = sum(1 for dim in nfr.values() for v in dim.values() if v is not None)
        print(f"  {rid[:24]:24} {typ:8} 功能分={f} NFR={ones}/{tot}" + ("" if d.get("build_ok", True) else " 构建×"))
    except Exception:
        pass
