# -*- coding: utf-8 -*-
import json, glob, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
B = r"D:\code-bench-v2\backup_clean"
DIMS = ["CMP","MTN","PERF","PTB","RLY","SEC"]
AGENTS = ["claude","codex","cursor","kimi","agy"]
LAB = {"claude":"Claude","codex":"Codex","cursor":"Cursor","kimi":"Kimi","agy":"agy"}
ds = sorted({p.split(os.sep)[-4] for p in glob.glob(B+r"\out\*\07_exam\grader\nfr_applicable.json")})
denom = {d:0 for d in DIMS}
for rid in ds:
    try:
        appl = json.load(open(os.path.join(B,"out",rid,"07_exam","grader","nfr_applicable.json"),encoding="utf-8"))["applicable"]
    except: continue
    for m in appl:
        d = m.get("dimension")
        if d in denom: denom[d]+=1
num = {a:{d:0 for d in DIMS} for a in AGENTS}
graded = {a:0 for a in AGENTS}
for rid in ds:
    for a in AGENTS:
        p = os.path.join(B,"chuti-run","grades",rid,a,"score.json")
        if not os.path.exists(p): continue
        try: nfr = json.load(open(p,encoding="utf-8")).get("nfr_by_dimension",{})
        except: continue
        graded[a]+=1
        for d in DIMS:
            num[a][d] += sum(1 for v in nfr.get(d,{}).values() if v==1)
print(f"数据集题数: {len(ds)}  (固定分母,所有agent一致)")
print("各维度适用指标总数(固定分母): " + "  ".join(f"{d}={denom[d]}" for d in DIMS) + f"  总={sum(denom.values())}")
print()
print("Agent".ljust(8) + "".join(d.ljust(16) for d in DIMS) + "总计")
for a in AGENTS:
    row = LAB[a].ljust(8); tn=0
    for d in DIMS:
        r = num[a][d]/denom[d]*100 if denom[d] else 0
        row += f"{num[a][d]}/{denom[d]}={r:.2f}%".ljust(16); tn+=num[a][d]
    td = sum(denom.values())
    row += f"{tn}/{td}={tn/td*100:.2f}%"
    print(row)
print()
print("(参考)各agent已判题数:", graded)
