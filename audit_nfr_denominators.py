#!/usr/bin/env python3
import json
import pathlib
from collections import Counter, defaultdict

BASE = pathlib.Path("/mnt/yangh559/chuti-run/grades")
AGENTS = ["claude", "codex", "cursor", "kimi"]
EXCLUDE = {"dosisod-refurb"}
DIMS = ["CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]

out = {"agents": {}, "overall": {}}
overall_dim = defaultdict(Counter)
overall_metric = defaultdict(Counter)

for agent in AGENTS:
    dim_counts = defaultdict(Counter)
    metric_counts = defaultdict(Counter)
    projects = build_fail = 0
    for sp in BASE.glob(f"*/{agent}/score.json"):
        rid = sp.parts[-3]
        if rid in EXCLUDE:
            continue
        projects += 1
        score = json.loads(sp.read_text(encoding="utf-8"))
        build_ok = bool(score.get("build_ok"))
        if not build_ok:
            build_fail += 1
        nfr = score.get("nfr_by_dimension", {}) or {}
        for dim, metrics in nfr.items():
            for mid, value in (metrics or {}).items():
                bucket = "build_ok_true" if build_ok else "build_ok_false"
                if value is None:
                    dim_counts[dim][f"{bucket}_none"] += 1
                    metric_counts[(dim, mid)][f"{bucket}_none"] += 1
                else:
                    dim_counts[dim][f"{bucket}_den"] += 1
                    metric_counts[(dim, mid)][f"{bucket}_den"] += 1
                    if value == 1:
                        dim_counts[dim][f"{bucket}_one"] += 1
                        metric_counts[(dim, mid)][f"{bucket}_one"] += 1
                    else:
                        dim_counts[dim][f"{bucket}_zero"] += 1
                        metric_counts[(dim, mid)][f"{bucket}_zero"] += 1

    out["agents"][agent] = {
        "projects": projects,
        "build_fail": build_fail,
        "dimensions": {
            dim: {
                "reported_den": dim_counts[dim]["build_ok_true_den"] + dim_counts[dim]["build_ok_false_den"],
                "reported_one": dim_counts[dim]["build_ok_true_one"] + dim_counts[dim]["build_ok_false_one"],
                "build_ok_true_den": dim_counts[dim]["build_ok_true_den"],
                "build_ok_true_one": dim_counts[dim]["build_ok_true_one"],
                "build_ok_false_den": dim_counts[dim]["build_ok_false_den"],
                "build_ok_false_zero": dim_counts[dim]["build_ok_false_zero"],
                "build_ok_true_none": dim_counts[dim]["build_ok_true_none"],
                "build_ok_false_none": dim_counts[dim]["build_ok_false_none"],
            }
            for dim in DIMS
        },
        "metrics": {
            f"{dim}.{mid}": dict(c)
            for (dim, mid), c in sorted(metric_counts.items())
        },
    }
    for dim, c in dim_counts.items():
        overall_dim[dim].update(c)
    for key, c in metric_counts.items():
        overall_metric[key].update(c)

out["overall"] = {
    "dimensions": {
        dim: {
            "reported_den": overall_dim[dim]["build_ok_true_den"] + overall_dim[dim]["build_ok_false_den"],
            "reported_one": overall_dim[dim]["build_ok_true_one"] + overall_dim[dim]["build_ok_false_one"],
            "build_ok_true_den": overall_dim[dim]["build_ok_true_den"],
            "build_ok_true_one": overall_dim[dim]["build_ok_true_one"],
            "build_ok_false_den": overall_dim[dim]["build_ok_false_den"],
            "build_ok_false_zero": overall_dim[dim]["build_ok_false_zero"],
            "build_ok_true_none": overall_dim[dim]["build_ok_true_none"],
            "build_ok_false_none": overall_dim[dim]["build_ok_false_none"],
        }
        for dim in DIMS
    },
    "metrics": {
        f"{dim}.{mid}": dict(c)
        for (dim, mid), c in sorted(overall_metric.items())
    },
}

print(json.dumps(out, ensure_ascii=False, indent=2))
