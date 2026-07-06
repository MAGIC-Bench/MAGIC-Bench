"""B+C end-to-end: exam spec -> candidate agent generates a project -> build cand-image
-> grade against the frozen black-box tests -> score.

  python run_candidate.py --repo <id> --candidate-engine codex --candidate-id cand1
  python run_candidate.py --repo <id> --candidate-engine claude --candidate-id A --model <m>

Requires the exam (Stages 1-5) to have run for <id> (reads out/<id>/). Writes
candidates/<id>/<candidate-id>/{SPEC/, <generated project>, report.json}.

The candidate agent is the SYSTEM UNDER EVALUATION; it only sees the candidate-facing
spec, never the hidden tests. grade.grade_suite drives the cand-image through the same
scenario backend (cli/service/pipeline) the golden was captured with.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
for _d in ("engine", "agent"):
    sys.path.insert(0, str(ROOT / _d))
sys.path.insert(0, str(ROOT))
import candidate
import grade


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--candidate-engine", choices=["codex", "claude"], default="codex")
    ap.add_argument("--candidate-id", default="cand1")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    repo_out = ROOT / "out" / args.repo
    rm_path = repo_out / "01_repo-model.json"
    if not rm_path.exists():
        sys.exit(f"ERROR: {rm_path} missing — run the exam (Stages 1-5) for {args.repo} first")
    rm = json.loads(rm_path.read_text(encoding="utf-8"))
    scenario_type = rm["scenario_type"]
    tests_dir = repo_out / "05_tests"
    if not any(tests_dir.glob("*.json")):
        sys.exit(f"ERROR: no tests in {tests_dir} — run Stage 5 first")

    cand_dir = ROOT / "candidates" / args.repo / args.candidate_id
    image = f"cand-{args.repo}-{args.candidate_id}:latest".lower()
    report = {"repo": args.repo, "candidate_id": args.candidate_id,
              "candidate_engine": args.candidate_engine, "scenario_type": scenario_type,
              "image": image}

    print(f"[{args.repo}/{args.candidate_id}] generating via {args.candidate_engine} ...")
    candidate.generate(repo_out, scenario_type, cand_dir,
                       engine=args.candidate_engine, model=args.model)

    print(f"[{args.repo}/{args.candidate_id}] building cand-image {image} ...")
    ok, err = candidate.build_image(cand_dir, image)
    if not ok:
        report.update({"build": "FAIL", "build_error": err, "score": {"run_gate": 0, "functional": 0.0}})
        (cand_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  BUILD FAILED: {err}")
        sys.exit(2)
    report["build"] = "OK"

    print(f"[{args.repo}/{args.candidate_id}] grading against {tests_dir} ...")
    modules = [m["id"] for m in json.loads((repo_out / "03_modules.json").read_text(encoding="utf-8"))["modules"]]
    cand_config = {"repo_id": args.repo, "scenario_type": scenario_type,
                   "runtime": {"mode": "docker"}, "image": image}
    for k in ("service", "pipeline"):
        if rm.get(k):
            cand_config[k] = rm[k]
    results = grade.grade_suite(cand_config, tests_dir)
    sc = grade.score(results, modules)
    report["score"] = {"run_gate": 1, **sc}
    report["failures"] = [r["id"] for r in results if not r["ok"]][:30]
    (cand_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  build OK | functional={sc['functional']:.3f} | passed {sc['passed']}/{sc['total']}")
    print(f"  per-module: {json.dumps(sc['per_module_passrate'])}")
    print(f"  report -> {cand_dir / 'report.json'}")


if __name__ == "__main__":
    main()
