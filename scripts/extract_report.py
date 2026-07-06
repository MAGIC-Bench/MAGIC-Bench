import re, json, pathlib, html as ht
P = pathlib.Path(r"C:\Users\16611\AppData\Roaming\Claude\local-agent-mode-sessions\f9b20565-7a07-43a1-9132-d53a519015b4\417d732e-5246-4abc-99b9-c718780f9c37\local_0efcdd53-aba7-4f2d-b7f8-74f6c8ccf94b\outputs\final_report.html")
s = P.read_text(encoding="utf-8", errors="replace")

def strip(x):
    return ht.unescape(re.sub(r"<[^>]+>", "", x)).strip()

scenarios = []
for dm in re.finditer(r"<details[^>]*>(.*?)</details>", s, re.S):
    block = dm.group(1)
    sm = re.search(r'class="dn">(.*?)</span>.*?class="ds">(.*?)</span>', block, re.S)
    if not sm:
        continue
    scen = strip(sm.group(1)); count = strip(sm.group(2))
    repos = []
    for rm in re.finditer(r"<tr>(.*?)</tr>", block, re.S):
        row = rm.group(1)
        if "<th" in row:
            continue
        am = re.search(r'<a class="repo"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', row, re.S)
        if not am:
            continue
        url = am.group(1); name = strip(am.group(2))
        tds = [strip(t) for t in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        fm = re.search(r'class="form f-(\w+)"', row)
        form = fm.group(1) if fm else (tds[2] if len(tds) > 2 else "")
        lang = tds[3] if len(tds) > 3 else ""
        build = tds[4] if len(tds) > 4 else ""
        src = tds[5] if len(tds) > 5 else ""
        repos.append({"name": name, "url": url, "form": form, "lang": lang, "build": build, "src": src})
    scenarios.append({"scenario": scen, "count_label": count, "n": len(repos), "repos": repos})

pathlib.Path(r"D:\code-bench\scripts\report-data.json").write_text(
    json.dumps(scenarios, ensure_ascii=False, indent=1), encoding="utf-8")

# readable summary
out = [f"TOTAL scenarios: {len(scenarios)}   repos: {sum(x['n'] for x in scenarios)}"]
for sc in scenarios:
    forms = {}
    langs = {}
    for r in sc["repos"]:
        forms[r["form"]] = forms.get(r["form"], 0) + 1
        langs[r["lang"]] = langs.get(r["lang"], 0) + 1
    out.append(f"\n## {sc['scenario']}  ({sc['count_label']}) -> {sc['n']} rows")
    out.append(f"   forms: {forms}")
    out.append(f"   langs: {dict(sorted(langs.items(), key=lambda x:-x[1]))}")
pathlib.Path(r"D:\code-bench\scripts\report-summary.txt").write_text("\n".join(out), encoding="utf-8")
print("done:", len(scenarios), "scenarios,", sum(x["n"] for x in scenarios), "repos")
