#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== overall status (14 repos) ==="
python3 - <<'PY'
import json, pathlib
out = pathlib.Path("out")
ids = [r["id"] for r in json.load(open("dataset/pilot-v2.manifest.json"))["repos"]]
done = []
for r in ids:
    s = out / r / "STATUS.json"
    st = json.loads(s.read_text()) if s.exists() else {}
    p = sorted(int(k) for k, v in st.items() if v == "pass")
    f = [k for k, v in st.items() if v != "pass"]
    tag = "DONE" if st.get("8") == "pass" else (f"stage{f[0]} FAIL" if f else (f"s{p[-1]}" if p else "-"))
    print(f"  {r:34} {tag}")
    if st.get("8") == "pass":
        done.append(r)
print("\n=== DONE repos: exam size (to pick lightweight) ===")
for r in done:
    ex = out / r / "07_exam"
    cand = ex / "candidate"
    ntests = len(list((ex / "grader" / "cases").glob("*.json"))) if (ex / "grader" / "cases").exists() else 0
    try:
        mods = json.loads((out / r / "03_modules.json").read_text())
        nmods = len(mods.get("modules", mods if isinstance(mods, list) else []))
    except Exception:
        nmods = "?"
    lang = (cand / "generation_language.txt").read_text().strip() if (cand / "generation_language.txt").exists() else "?"
    cdoc = sum(p.stat().st_size for p in cand.glob("*")) if cand.exists() else 0
    contract = [p.name for p in cand.glob("02_*")]
    print(f"  {r:30} lang={lang:7} tests={ntests:<4} modules={nmods} candidate_bytes={cdoc} contract={contract}")
PY
