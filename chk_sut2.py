# -*- coding: utf-8 -*-
import json, glob, os, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
EXAMS = r"D:\code-bench-v2\backup_clean\chuti-run\exams"
man = json.load(open(r"D:\code-bench-v2\dataset\repo-list.manifest.json", encoding="utf-8"))
rows = man if isinstance(man, list) else man.get("repos", man.get("items", []))
exam_ids = set(os.path.basename(d) for d in glob.glob(EXAMS + r"\*"))

print("最终 82 卷面 SUT 类型: 全部 cli(0 service)")
print("清单 121 仓 SUT 类型: cli=99, service=22\n")
svc = [x for x in rows if x.get("scenario_type") == "service"]
print(f"清单里 22 个 service 仓,有几个进了最终 82 卷面:")
inn = sum(1 for x in svc if x["id"] in exam_ids)
print(f"  进了卷面: {inn} / 22\n")
print("这 22 个 service 仓(领域 / 可行性 / 是否进卷面):")
for x in svc:
    fe = x.get("feasibility", x.get("_feasibility", "?"))
    fr = x.get("_friction", x.get("friction", []))
    inx = "进卷面" if x["id"] in exam_ids else "未进"
    print(f"  {x['id'][:34]:34} {x.get('scenario','?'):22} 可行={fe} {inx}  摩擦={fr}")
