#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("out")

rows = {}
counts = Counter()
examples = defaultdict(list)

for fp in ROOT.rglob("07_exam/grader/measurable_metrics.json"):
    rid = fp.parts[1] if len(fp.parts) > 1 else fp.parent.parent.parent.name
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue
    for m in data.get("measurable", []):
        method = str(m.get("method", "")).lower()
        if method == "static":
            mid = m.get("metric_id")
            if not mid:
                continue
            counts[mid] += 1
            rows.setdefault(mid, {
                "metric_id": mid,
                "probe": m.get("probe", ""),
                "pass_if": m.get("pass_if", ""),
                "fairness": m.get("fairness", ""),
            })
            if len(examples[mid]) < 5:
                examples[mid].append(rid)

print(json.dumps({
    "count_static_metric_ids": len(rows),
    "metrics": [
        {**rows[mid], "repo_count": counts[mid], "examples": examples[mid]}
        for mid in sorted(rows)
    ],
}, ensure_ascii=False, indent=2))
