"""Parse the qualification HTML's '合格标的清单（去重）' table into a scheme manifest."""
import re, json, pathlib
from collections import Counter

HTML = r"D:\腾讯电脑管家软件搬家\C盘清理文件搬家\xwechat_files\wxid_7zznq25t7x1f22_eb6b\msg\file\2026-06\index-1b418970.html"
OUT = r"D:\code-bench\dataset\codegen-bench.manifest.json"

html = pathlib.Path(HTML).read_text(encoding="utf-8", errors="replace")
start = html.index("合格标的清单")
seg = html[start: html.index("</table>", start)]

TYPE = {"CLI": "cli", "Service": "service", "Pipeline": "pipeline"}
repos, seen, unmapped = [], set(), []

for row in seg.split("<tr>"):
    m_url = re.search(r'href="(https://github\.com/[^"]+)"', row)
    if not m_url:
        continue
    url = m_url.group(1).rstrip("/")
    name = url.split("github.com/", 1)[1]
    if name.lower() in seen:
        continue
    seen.add(name.lower())
    typ = (re.search(r'cat cat-pass">(\w+)', row) or [None, ""])[1]
    st = TYPE.get(typ)
    if st is None:
        unmapped.append((name, typ))
    meta = (re.search(r'class="meta">([^<]+)</td>', row) or [None, ""])[1].strip()
    reason = (re.search(r'class="reason">([^<]+)</td>', row) or [None, ""])[1].strip()
    repos.append({
        "id": re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'),
        "scenario": meta.split("、")[0] if meta else "",
        "scenario_type": st,
        "language": "unknown",
        "source": {"kind": "git", "url": url + ".git", "ref": None},
        "_repo": name,
        "_all_scenarios": meta,
        "_type_label": typ,
        "_reason": reason,
    })

manifest = {
    "dataset": "codegen-bench-qualified",
    "defaults": {"quota": 20, "runtime_mode": "docker"},
    "_note": "Exported from the qualification HTML (合格标的清单 去重). scenario_type<-类型, scenario<-所属场景. LANGUAGE='unknown' (not in source) -> fill per repo before running; PIN source.ref (commit) for reproducibility. _* fields are reference metadata.",
    "repos": repos,
}
pathlib.Path(OUT).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

print("total repos:", len(repos))
print("by scenario_type:", dict(Counter(r["scenario_type"] for r in repos)))
print("by scenario (domain):", dict(Counter(r["scenario"] for r in repos)))
print("unmapped type rows:", unmapped)
print("written:", OUT)
print("\nsample[0]:", json.dumps(repos[0], ensure_ascii=False))
