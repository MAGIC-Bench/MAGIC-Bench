import re, json, pathlib

data = json.loads(pathlib.Path(r"D:\code-bench\scripts\report-data.json").read_text(encoding="utf-8"))
pilot = json.loads(pathlib.Path(r"D:\code-bench\dataset\pilot-v2.manifest.json").read_text(encoding="utf-8"))
PILOT = {r["id"] for r in pilot["repos"]}
FORM = {"cli": "CLI", "pipe": "Pipeline", "svc": "Service"}


def rid(url):
    return re.sub(r"[^a-z0-9]+", "-", url.split("github.com/", 1)[-1].lower()).strip("-")


md = ["# 新仓库清单 v2 — 按 5 场景分类(共 216) \n",
      "> ⭐ = 新 pilot 选中(每场景 3 个)。完整 manifest:`dataset/codegen-bench-v2.manifest.json`;pilot:`dataset/pilot-v2.manifest.json`\n"]
for sc in data:
    md.append(f"\n## {sc['scenario']}  ({sc['count_label']})\n")
    md.append("| # | 仓库 | 形态 | 语言 | 构建 | |")
    md.append("|---|---|---|---|---|---|")
    for i, r in enumerate(sc["repos"], 1):
        star = "⭐" if rid(r["url"]) in PILOT else ""
        md.append(f"| {i} | [{r['name']}]({r['url']}) | {FORM.get(r['form'], r['form'])} | {r['lang']} | `{r['build']}` | {star} |")
pathlib.Path(r"D:\code-bench\dataset\repo-list-v2.md").write_text("\n".join(md), encoding="utf-8")
print("wrote dataset/repo-list-v2.md :", sum(x["n"] for x in data), "repos in", len(data), "categories")
