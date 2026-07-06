"""Stage 7 verify - prove the exam is sound before shipping it.

high_water : run the whole suite against the ORIGINAL. Cases the original itself FAILS have
             bad/unstable golden (e.g. a frozen timeout-124, or a value the double-run missed)
             -> they are DROPPED (moved to 05_tests_dropped/), then high_water is recomputed on the
             survivors. gate_stage7 then fails the repo if the drop-rate is too high (the original
             can't pass its own exam -> poisoned exam; e.g. cisco high-water 0.89 wrongly shipped).

(Mutation was removed in v2: it was gron-specific, complex to implement generically, and cannot be
 aligned across languages -- a go repo and a python repo could never share a mutant set.)
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import grade


def high_water(config, tests_dir):
    results = grade.grade_suite(config, tests_dir)
    passed = sum(1 for r in results if r["ok"])
    return passed, len(results), [r for r in results if not r["ok"]]


def run(repo_out, repo_src, config, bin_dir):
    repo_out = pathlib.Path(repo_out)
    tests_dir = repo_out / "05_tests"
    p, t, failures = high_water(config, tests_dir)
    dropped = []
    if failures:
        # the ORIGINAL fails its own golden on these -> bad/unstable golden -> drop them
        drop_dir = repo_out / "05_tests_dropped"
        drop_dir.mkdir(exist_ok=True)
        fail_ids = {f["id"] for f in failures}
        for fp in list(tests_dir.rglob("*.json")):
            try:
                cid = json.loads(fp.read_text(encoding="utf-8")).get("id")
            except Exception:
                continue
            if cid in fail_ids:
                fp.rename(drop_dir / fp.name)
                dropped.append(cid)
        p, t, failures = high_water(config, tests_dir)          # recompute on survivors
    denom = t + len(dropped)
    drop_rate = (len(dropped) / denom) if denom else 0.0
    report = {"high_water": {"passed": p, "total": t, "rate": (p / t if t else 0.0),
                             "dropped": len(dropped), "drop_rate": round(drop_rate, 4),
                             "dropped_ids": dropped[:50],
                             "failures": [f["id"] for f in failures]}}
    (repo_out / "07_verify.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
