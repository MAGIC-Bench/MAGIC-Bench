"""Direct audit of the pilot-v3 output for the 5 reported quality defects (real counts)."""
import json, pathlib, re, sys
sys.path.insert(0, r"D:\code-bench-v2\engine")
import deident

OUT = pathlib.Path(r"D:\code-bench-v2\out")
REPOS = {"dosisod-refurb": "refurb", "josephburnett-jd": "jd", "ogen-go-ogen": "ogen"}


def load_cases(rid):
    d = OUT / rid / "07_exam" / "grader" / "cases"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))] if d.exists() else []


def val_text(a):
    v = a.get("value")
    if isinstance(v, dict):
        return v.get("utf8") or v.get("b64") or str(v.get("int", "")) or ""
    return str(v) if v is not None else ""


for rid, binary in REPOS.items():
    cases = load_cases(rid)
    rmp = OUT / rid / "01_repo-model.json"
    rm = json.loads(rmp.read_text(encoding="utf-8")) if rmp.exists() else {}
    toks = deident.identity_tokens(rm.get("repo_id", rid), binary)
    print(f"\n########## {rid}  (id-tokens={toks}, {len(cases)} cases) ##########")

    # #1 golden values containing an identity token under exact/normalized
    leak1 = []
    for c in cases:
        for a in c.get("assertions", []):
            if a.get("class") in ("exact", "normalized"):
                t = val_text(a)
                hits = [tok for tok in toks if re.search(re.escape(tok), t, re.I)]
                if hits:
                    leak1.append((c["id"], a["field"], hits, t[:50].replace("\n", "\\n")))
    print(f"[#1 id-token in EXACT/NORMALIZED golden] {len(leak1)} assertions; e.g.:")
    for x in leak1[:4]:
        print("    ", x)
    cc = list((OUT / rid / "07_exam" / "candidate").glob("02_*.json"))
    if cc:
        ct = cc[0].read_text(encoding="utf-8")
        print(f"    candidate contract: 'app' present={'app' in ct} | '{binary}' present={binary in ct.lower()}")

    # #6 argv element containing an identity token
    leak6 = []
    for c in cases:
        for el in (c.get("input", {}).get("argv", []) or []):
            if any(re.search(re.escape(tok), str(el), re.I) for tok in toks):
                leak6.append((c["id"], list(c["input"]["argv"])[:6]))
                break
    print(f"[#6 id-token in argv input] {len(leak6)} cases; e.g.:")
    for x in leak6[:4]:
        print("    ", x[0], x[1])

    # #3 exact/normalized on help/version/internal symbols
    pats = ["usage", "Usage", "Version", "version", "--help", "Mypy", "MypyFile", "ExpressionStmt",
            "Traceback", "0.0.0", "HEAD"]
    leak3 = {}
    for c in cases:
        for a in c.get("assertions", []):
            if a.get("class") in ("exact", "normalized"):
                t = val_text(a)
                for p in pats:
                    if p in t:
                        leak3.setdefault(p, set()).add(c["id"])
    print("[#3 impl-detail under exact/normalized]:")
    for p, ids in leak3.items():
        print(f"    '{p}': {len(ids)} cases (e.g. {list(ids)[:2]})")
    if not leak3:
        print("     none found")

    classes = {}
    for c in cases:
        for a in c.get("assertions", []):
            classes[a.get("class")] = classes.get(a.get("class"), 0) + 1
    print(f"[assertion classes] {classes}")

    # #2 adversarial open_critical
    advp = OUT / rid / "06_adversarial.json"
    if advp.exists():
        adv = json.loads(advp.read_text(encoding="utf-8"))
        print(f"[#2 06_adversarial] open_critical={adv.get('open_critical')} | keys={list(adv.keys())}")
        crit = adv.get("findings") or adv.get("issues") or adv.get("critical") or []
        if isinstance(crit, list):
            for it in crit[:3]:
                print("      -", json.dumps(it, ensure_ascii=False)[:160])

# #4 jd malformed vs contract
print("\n########## ISSUE 4: jd malformed-input vs contract exit codes ##########")
jd = OUT / "josephburnett-jd"
chid = list(jd.glob("02_*.json"))
contract = json.loads(chid[0].read_text(encoding="utf-8")) if chid else {}
print("contract exit_codes:", contract.get("exit_codes"))
print("contract candidate_delivery/io:", {k: contract.get(k) for k in ("candidate_delivery", "io_contract") if contract.get(k)})
hits = 0
for c in load_cases("josephburnett-jd"):
    blob = (c.get("id", "") + json.dumps(c.get("input", {}), ensure_ascii=False)).lower()
    if any(k in blob for k in ("malform", "invalid", "bad", "garbage", "notjson", "not-json", "syntax", "broken")):
        exitv = next((a.get("value") for a in c.get("assertions", []) if a["field"] == "exit"), None)
        print(f"   {c['id'][:55]:55s} golden_exit={exitv} input={json.dumps(c.get('input',{}),ensure_ascii=False)[:70]}")
        hits += 1
if not hits:
    print("   (no obviously-malformed-input cases matched by keyword)")
