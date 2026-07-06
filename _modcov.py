# -*- coding: utf-8 -*-
import json, glob, statistics as st, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
cov1=[];covq=[];m1=mq=mt=0
for p in glob.glob(r"D:\code-bench-v2\out_server_backup\*\05_coverage-ledger.json"):
    try:
        s=json.load(open(p,encoding="utf-8"))["summary"]
        pm=s.get("per_module",{})
        if not pm: continue
        tot=len(pm)
        has1=sum(1 for c in pm.values() if c>=1)   # ≥1 用例 = 覆盖
        atq=sum(1 for c in pm.values() if c>=20)
        mt+=tot; m1+=has1; mq+=atq
        cov1.append(has1/tot); covq.append(atq/tot)
    except: pass
print(f"样本 14 仓,总模块 {mt}")
print(f"模块覆盖率【≥1用例即覆盖,你的定义】: 各仓均值 {st.mean(cov1)*100:.1f}%  整体 {m1}/{mt}={m1/mt*100:.1f}%")
print(f"对比·模块达满配额20: 各仓均值 {st.mean(covq)*100:.1f}%  整体 {mq}/{mt}={mq/mt*100:.1f}%")
