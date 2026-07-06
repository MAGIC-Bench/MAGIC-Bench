#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path("/mnt/yangh559/code-bench-v2/out")
EXCLUDE = {"dosisod-refurb"}

rows = {}
counts = Counter()
examples = defaultdict(list)
projects = 0

for fp in sorted(OUT.glob("*/07_exam/grader/nfr_applicable.json")):
    rid = fp.parts[-4]
    if rid in EXCLUDE:
        continue
    projects += 1
    data = json.loads(fp.read_text(encoding="utf-8"))
    for m in data.get("applicable", []):
        if m.get("kind") != "static":
            continue
        mid = m["metric_id"]
        rows.setdefault(mid, {
            "metric_id": mid,
            "dimension": m.get("dimension"),
            "name": m.get("name"),
            "desc": m.get("desc"),
            "kind": m.get("kind"),
        })
        counts[mid] += 1
        if len(examples[mid]) < 8:
            examples[mid].append(rid)

print(json.dumps({
    "projects": projects,
    "static_metric_ids": len(rows),
    "metrics": [
        {**rows[mid], "repo_count": counts[mid], "examples": examples[mid]}
        for mid in sorted(rows)
    ],
}, ensure_ascii=False, indent=2))
