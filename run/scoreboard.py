#!/usr/bin/env python3
"""成绩矩阵:题 × agent → 功能分 + NFR 维度命中。读 /mnt/yangh559/chuti-run/grades/<id>/<type>/score.json。"""
import glob, json, os

GRADES = "/mnt/yangh559/chuti-run/grades"
AGENTS = ["codex", "claude", "kimi", "cursor", "antigravity"]

rows = {}
for sj in glob.glob(os.path.join(GRADES, "*", "*", "score.json")):
    typ = os.path.basename(os.path.dirname(sj))
    rid = os.path.basename(os.path.dirname(os.path.dirname(sj)))
    try:
        s = json.load(open(sj, encoding="utf-8"))
    except Exception:
        continue
    rows.setdefault(rid, {})[typ] = s

if not rows:
    print("还没有成绩。等考试节点提交 + 判卷节点判完。")
    raise SystemExit(0)

def cell(s):
    if not s:
        return "    -   "
    if not s.get("build_ok", True):
        return "  构建×  "
    f = s.get("功能分", 0)
    nfr = s.get("nfr_by_dimension", {})
    ones = sum(1 for dim in nfr.values() for v in dim.values() if v == 1)
    tot = sum(1 for dim in nfr.values() for v in dim.values() if v is not None)
    return f" {f:.2f}|{ones}/{tot} "

hdr = "题".ljust(26) + "".join(a[:8].center(10) for a in AGENTS)
print(hdr); print("-" * len(hdr))
for rid in sorted(rows):
    line = rid[:24].ljust(26) + "".join(cell(rows[rid].get(a)).center(10) for a in AGENTS)
    print(line)
print("\n格 = 功能分|NFR命中数/可测数 ; 构建× = 构建/冒烟失败全 0")
