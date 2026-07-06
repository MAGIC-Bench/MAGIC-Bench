# -*- coding: utf-8 -*-
import json, glob, os, statistics as st, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
EXT = {".rs",".go",".py",".js",".ts",".tsx",".jsx",".java",".c",".cc",".cpp",".h",".hpp",".rb",".cs",".php",".kt",".swift",".scala",".pl",".ex",".lua",".sh"}
SKIP = ("\\.git\\","\\target\\","\\node_modules\\","\\vendor\\","\\build\\","\\dist\\","\\.venv\\","\\__pycache__\\")
def stats(repo):
    nf=loc=0
    for root,dirs,files in os.walk(repo):
        if any(s in (root+"\\") for s in SKIP): dirs[:]=[]; continue
        for f in files:
            if os.path.splitext(f)[1].lower() in EXT:
                nf+=1
                try:
                    with open(os.path.join(root,f),"rb") as fh: loc+=sum(1 for _ in fh)
                except: pass
    return nf,loc
# 文件/LOC:本地 repos\(5个)
fc=[];locs=[]
for d in glob.glob(r"D:\code-bench-v2\repos\*"):
    if os.path.isdir(d):
        nf,lc=stats(d)
        if nf: fc.append((os.path.basename(d),nf,lc))
print("=== 本地 repos\\ 文件数/LOC(样本", len(fc), "仓,仅供参考) ===")
for rid,nf,lc in fc: print(f"   {rid:28} 文件 {nf:>5}  LOC {lc:>7}")
if fc:
    print(f"   文件数 中位数 {st.median([x[1] for x in fc]):.0f}  LOC 中位数 {st.median([x[2] for x in fc]):.0f}")
# 覆盖率:out_server_backup(14个)
pcts=[];modcov=[];mt=mq=0
for p in glob.glob(r"D:\code-bench-v2\out_server_backup\*\05_coverage-ledger.json"):
    try:
        s=json.load(open(p,encoding="utf-8"))["summary"]
        pct=s.get("pct_statements") or 0
        if pct>0: pcts.append(pct)
        pm=s.get("per_module",{})
        if pm: tot=len(pm);atq=sum(1 for m,c in pm.items() if c>=20);mt+=tot;mq+=atq;modcov.append(atq/tot)
    except: pass
print(f"\n=== out_server_backup 覆盖率(样本 14 仓) ===")
print(f"   行覆盖率(仅Go原仓>0): 有覆盖 {len(pcts)}/14  均值 {st.mean(pcts) if pcts else 0:.1f}%")
print(f"   模块覆盖率(达配额20/总模块): 各仓均值 {st.mean(modcov)*100:.1f}%  整体 {mq}/{mt}={mq/mt*100:.1f}%")
