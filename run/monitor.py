#!/usr/bin/env python3
"""出题流水线单帧快照(被 monitor.sh 循环刷新)。用法: monitor.py [manifest]"""
import glob, json, os, sys

PREFIX = "/mnt/yangh559"; CODE = f"{PREFIX}/code-bench-v2"; ST = f"{PREFIX}/chuti-run"
MAN = sys.argv[1] if len(sys.argv) > 1 else f"{CODE}/dataset/repo-list.manifest.json"
STAGE = ["0 ingest", "1 comprehend", "2 contract", "3 modules", "4 nfr-label",
         "5 testgen", "6 adversarial", "7 verify", "8 package"]

try:
    repos = json.load(open(MAN, encoding="utf-8"))["repos"]
except Exception as e:
    print("读不到清单", MAN, e); sys.exit(0)

done = {os.path.basename(p) for p in glob.glob(f"{ST}/done/*")}
failed = {os.path.basename(p) for p in glob.glob(f"{ST}/failed/*")}
skipped = {os.path.basename(p) for p in glob.glob(f"{ST}/skip/*")}
exams = {os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{ST}/exams/*/READY")}
claims = {}
for p in glob.glob(f"{ST}/claims/*/owner"):
    try: claims[os.path.basename(os.path.dirname(p))] = open(p).read().split()[0]
    except Exception: pass

ids = [r["id"] for r in repos]
nd = len(done & set(ids)); nsk = len(skipped & set(ids))
nrem = len(ids) - nd - nsk - len(failed & set(ids)) - len(claims)
print(f"出题进度: 完成 {nd}/{len(ids)} | 失败 {len(failed & set(ids))} | ⊘跳过 {nsk} | 已发布考卷 {len(exams & set(ids))}"
      f" | 进行中 {len(claims)} | 剩 {max(nrem,0)}")
print(f"{'仓库':<26}{'语言':<11}{'阶段':<16}{'状态':<7}{'节点/备注'}")
print("-" * 78)
for r in repos:
    rid = r["id"]; lang = r.get("language") or r.get("_lang") or "?"
    try: status = json.load(open(f"{CODE}/out/{rid}/STATUS.json"))
    except Exception: status = {}
    passed = [int(k) for k, v in status.items() if v == "pass"]
    failk = [int(k) for k, v in status.items() if str(v).startswith("fail")]
    cur = (max(passed) + 1) if passed else 0
    if rid in done:
        stage, stt, extra = "✓ 8 package", "DONE", ("📋已发卷" if rid in exams else "")
    elif rid in skipped:
        stage, stt, extra = "⊘ golden不可靠", "跳过", "永久跳过"
    elif rid in failed:
        stage = "✗ " + STAGE[failk[0]] if failk else STAGE[min(cur, 8)]
        stt, extra = "FAIL", ""
    elif rid in claims:
        stage, stt, extra = STAGE[min(cur, 8)], "跑中", claims[rid]
    else:
        stage, stt, extra = "-", "排队", ""
    print(f"{rid:<26}{lang:<11}{stage:<16}{stt:<7}{extra}")
