# -*- coding: utf-8 -*-
import json, glob, os, statistics, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
B = r"D:\code-bench-v2\backup_clean"
man = json.load(open(r"D:\code-bench-v2\dataset\repo-list.manifest.json", encoding="utf-8"))
rows = man if isinstance(man, list) else man.get("repos", [])
by = {x["id"]: x for x in rows}

# 数据集仓(有卷面的)
exam_rids = sorted(os.path.basename(d) for d in glob.glob(B + r"\chuti-run\exams\*") if os.path.isdir(d))
print(f"数据集仓数(卷面): {len(exam_rids)}")

# 测试用例数(grader/cases,即真正判分用的)
per = []
for rid in exam_rids:
    cdir = os.path.join(B, "out", rid, "07_exam", "grader", "cases")
    n = len(glob.glob(cdir + r"\*.json")) if os.path.isdir(cdir) else 0
    if n:
        per.append((rid, n))
counts = [n for _, n in per]
print(f"有 grader 的仓: {len(per)}")
print(f"测试用例总数: {sum(counts)}")
print(f"每仓用例数  均值: {statistics.mean(counts):.1f}  中位数: {statistics.median(counts):.0f}  最小/最大: {min(counts)}/{max(counts)}")

# star(数据集仓)
stars = [by[r].get("_stars", 0) for r in exam_rids if r in by]
print(f"\nstar 样本数: {len(stars)}")
print(f"原仓 star  均值: {statistics.mean(stars):.0f}  中位数: {statistics.median(stars):.0f}  最小/最大: {min(stars)}/{max(stars)}")
