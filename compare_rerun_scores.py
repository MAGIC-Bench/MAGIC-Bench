#!/usr/bin/env python3
import json
import pathlib
import sys
from collections import defaultdict

STATE = pathlib.Path("/mnt/yangh559/chuti-run")
SUMMARIES = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STATE / "rerun_case_metrics" / "all_project_summaries.json"
FUNC_KEY = "\u529f\u80fd\u5206"


def main():
    rows = json.loads(SUMMARIES.read_text(encoding="utf-8"))
    diffs = []
    for s in rows:
        score_path = STATE / "grades" / s["rid"] / s["agent"] / "score.json"
        score = json.loads(score_path.read_text(encoding="utf-8"))
        func = score.get(FUNC_KEY, 0.0)
        total = int(s.get("functional_total", 0))
        if isinstance(func, dict):
            old = int(func.get("passed", 0))
            total = int(func.get("total", total))
        else:
            old = int(round(float(func or 0.0) * total))
        new = int(s.get("functional_passed", 0))
        if old != new:
            diffs.append({
                "agent": s["agent"],
                "rid": s["rid"],
                "score_passed": old,
                "rerun_passed": new,
                "total": total,
                "delta": new - old,
                "rerun_build_gate_ok": s.get("rerun_build_gate_ok"),
                "rerun_error": s.get("rerun_error"),
            })

    by_agent = defaultdict(lambda: {"count": 0, "delta": 0})
    for d in diffs:
        by_agent[d["agent"]]["count"] += 1
        by_agent[d["agent"]]["delta"] += d["delta"]

    print(json.dumps({
        "diff_count": len(diffs),
        "delta_by_agent": by_agent,
        "diffs": diffs[:120],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
