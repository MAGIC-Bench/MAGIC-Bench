"""End-to-end: emit a grader, run grade.py against a fake candidate, check score.json."""
import json, os, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import pytest_emit

fails = []
def chk(n, c):
    print(("OK   " if c else "FAIL ") + n)
    if not c: fails.append(n)

repo = pathlib.Path(tempfile.mkdtemp())
(repo / "05_tests").mkdir(); (repo / "05_smoke").mkdir()
(repo / "05_tests" / "func1.json").write_text(json.dumps({"id": "func1", "modules": ["M1"], "scenario_type": "cli",
   "input": {"argv": ["ok"]}, "assertions": [{"field": "stdout", "class": "exact", "value": {"utf8": "ok"}}]}))
(repo / "05_tests" / "sec.json").write_text(json.dumps({"id": "sec", "modules": ["M1"], "scenario_type": "cli",
   "security_metric": "SEC5", "input": {"argv": ["bad"]}, "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:2"}]}))
(repo / "05_smoke" / "sm.json").write_text(json.dumps({"id": "sm", "modules": ["SMOKE"], "scenario_type": "cli", "smoke": True,
   "input": {"argv": ["--help"]}, "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:0"}]}))

grader = pathlib.Path(tempfile.mkdtemp()) / "grader"
pytest_emit.emit(repo, grader, "cli")
(grader / "nfr_applicable.json").write_text(json.dumps({"applicable": [
    {"metric_id": "PERF4", "dimension": "PERF", "kind": "runtime"},
    {"metric_id": "PERF1", "dimension": "PERF", "kind": "runtime"},
    {"metric_id": "PTB1", "dimension": "PTB", "kind": "runtime"},
    {"metric_id": "RLY4", "dimension": "RLY", "kind": "runtime"},
    {"metric_id": "SEC5", "dimension": "SEC", "kind": "runtime"},
    {"metric_id": "MTN1", "dimension": "MTN", "kind": "static"}]}))
chk("grade.py emitted", (grader / "grade.py").exists())
chk("nfr_score.py emitted", (grader / "nfr_score.py").exists())

cand = pathlib.Path(tempfile.mkdtemp()) / "cand.sh"
cand.write_text('#!/bin/bash\nif [ "$1" = "--help" ]; then echo h; exit 0; fi\n'
                'if [ "$1" = "bad" ]; then exit 2; fi\nprintf "%s" "$1"; exit 0\n')
cand.chmod(0o755)
env = dict(os.environ, CANDIDATE_BIN=str(cand), RLY4_MEM_KB="1048576")   # 1GB cap (generous: verify mode runs)
env.pop("CANDIDATE_SRC", None)
r = subprocess.run([sys.executable, str(grader / "grade.py")], capture_output=True, text=True, env=env)
if r.returncode != 0:
    print("grade.py stderr:", r.stderr[-500:])
score = json.loads((grader / "score.json").read_text(encoding="utf-8"))
print(json.dumps(score, ensure_ascii=False))
chk("build_ok true", score["build_ok"] is True)
chk("功能分 = 1.0 (1/1 functional passed)", score["功能分"] == 1.0)
chk("PERF4 = 1", score["nfr_by_dimension"]["PERF"]["PERF4"] == 1)
chk("PERF1 = 1", score["nfr_by_dimension"]["PERF"]["PERF1"] == 1)
chk("PTB1 = 1 (built)", score["nfr_by_dimension"]["PTB"]["PTB1"] == 1)
chk("RLY4 = 1 (graceful under mem cap)", score["nfr_by_dimension"]["RLY"]["RLY4"] == 1)
chk("SEC5 = 1 (security case passed 100%)", score["nfr_by_dimension"]["SEC"]["SEC5"] == 1)
chk("MTN1 = None (static, no codex in test)", score["nfr_by_dimension"]["MTN"]["MTN1"] is None)

print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
