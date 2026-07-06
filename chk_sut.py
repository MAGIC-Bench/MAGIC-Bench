import json, glob, os, collections
EXAMS = r"D:\code-bench-v2\backup_clean\chuti-run\exams"
man = json.load(open(r"D:\code-bench-v2\dataset\repo-list.manifest.json", encoding="utf-8"))
rows = man if isinstance(man, list) else man.get("repos", man.get("items", []))
by = {x["id"]: x for x in rows}

# 82 卷面 meta.json 的 scenario_type
ex = collections.Counter()
exam_ids = []
for d in glob.glob(EXAMS + r"\*"):
    rid = os.path.basename(d)
    exam_ids.append(rid)
    try:
        m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        ex[m.get("scenario_type")] += 1
    except Exception:
        ex["<无meta>"] += 1
print("【82 卷面】scenario_type 分布:", dict(ex))

# 121 清单
print("【121 清单】scenario_type:", dict(collections.Counter(x.get("scenario_type") for x in rows)))
print("【121 清单】scenario(领域):", dict(collections.Counter(x.get("scenario") for x in rows)))

# 清单里 service 类型的仓
svc = [x["id"] for x in rows if x.get("scenario_type") == "service"]
print(f"\n清单里 scenario_type=service 的仓: {len(svc)} 个")
for s in svc:
    inexam = "✓在82卷面" if s in exam_ids else "✗没进卷面"
    print(f"   {s}  {inexam}")

# web_api 领域的仓 -> 它们被定成什么 SUT
wa = [(x["id"], x.get("scenario_type"), x["id"] in exam_ids) for x in rows if x.get("scenario") == "web_api"]
print(f"\nweb_api 领域的仓 {len(wa)} 个,它们的 scenario_type:")
for rid, st, ine in wa:
    print(f"   {rid}  type={st}  {'在卷面' if ine else '没进卷面'}")
