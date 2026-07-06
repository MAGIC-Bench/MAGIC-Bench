"""Focused test for req 2.7 (security test cases) + req 2.8 (smoke suite) wiring."""
import json, pathlib, sys, tempfile, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
for sub in ("engine", "agent", "stages", "."):
    sys.path.insert(0, str(ROOT / sub))

fails = []
def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

import nfr_security, pytest_emit, stage5_loop, stage8_package

# ---- 1) nfr_security.pick_security_metrics (label-driven, ID-based SEC1/SEC4/SEC5) --------
ro = pathlib.Path(tempfile.mkdtemp())
(ro / "nfr-metrics.json").write_text(json.dumps({"metrics": [
    {"id": "SEC1", "name": "未授权读阻断", "dimension": "SEC", "kind": "runtime", "scoring": "ratio100"},
    {"id": "SEC4", "name": "未授权写阻断", "dimension": "SEC", "kind": "runtime", "scoring": "ratio100"},
    {"id": "SEC5", "name": "SQL注入防护", "dimension": "SEC", "kind": "runtime", "scoring": "ratio100"},
    {"id": "SEC2", "name": "无敏感信息硬编码", "dimension": "SEC", "kind": "static", "scoring": "binary"},
    {"id": "MTN1", "name": "无超大单文件", "dimension": "MTN", "kind": "static", "scoring": "binary"},
]}, ensure_ascii=False), encoding="utf-8")
(ro / "04_nfr-labels.json").write_text(json.dumps({
    "labels": [{"metric_id": "SEC1", "applies": True}, {"metric_id": "SEC5", "applies": True},
               {"metric_id": "SEC4", "applies": False}, {"metric_id": "SEC2", "applies": True},
               {"metric_id": "MTN1", "applies": True}],
    "applicable": ["SEC1", "SEC5", "SEC2", "MTN1"]}, ensure_ascii=False), encoding="utf-8")
picked = {p["metric_id"]: p["kind"] for p in nfr_security.pick_security_metrics(ro)}
check("picks applicable SEC1 (unauthorized_access)", picked.get("SEC1") == "unauthorized_access")
check("picks applicable SEC5 (malicious_input)", picked.get("SEC5") == "malicious_input")
check("excludes non-applicable SEC4", "SEC4" not in picked)
check("excludes static SEC2 (not black-box testable)", "SEC2" not in picked)
check("excludes non-security MTN1", "MTN1" not in picked)

# empty when no behavior-testable security metric applies
(ro / "04_nfr-labels.json").write_text(json.dumps(
    {"labels": [{"metric_id": "MTN1", "applies": True}], "applicable": ["MTN1"]}), encoding="utf-8")
check("empty when no security metric applicable", nfr_security.pick_security_metrics(ro) == [])

# ---- 2) smoke invocations (scenario-aware, input dicts) ---------------------
(ro / "00_runtime.json").write_text(json.dumps({"smoke": ["version"]}), encoding="utf-8")
invs = stage5_loop._smoke_invocations(ro, {"scenario_type": "cli"})
check("cli smoke includes configured {argv:['version']}", {"argv": ["version"]} in invs)
check("cli smoke includes universal --help/--version", {"argv": ["--help"]} in invs and {"argv": ["--version"]} in invs)
svc_inv = stage5_loop._smoke_invocations(ro, {"scenario_type": "service", "service": {"health": "/healthz"}})
check("service smoke is a health GET step", svc_inv == [{"steps": [{"method": "GET", "path": "/healthz"}]}])
check("pipeline smoke is a trivial run", stage5_loop._smoke_invocations(ro, {"scenario_type": "pipeline"}) == [{"files": {}}])
check("unknown scenario smoke empty", stage5_loop._smoke_invocations(ro, {"scenario_type": "weird"}) == [])

# ---- 2b) _smoke_spec fairness (no exact exit on a nonzero banner) -----------
class _Obs:
    def __init__(self, exit_code=0, stdout=b"", stderr=b"", out_files=None, http=None):
        self.exit_code, self.stdout, self.stderr = exit_code, stdout, stderr
        self.out_files = out_files or {}
        self.extra = {"http": http} if http else {}
spec0 = stage5_loop._smoke_spec(_Obs(exit_code=0, stdout=b"usage..."))
check("cli success smoke pins exit 0 + stdout nonempty",
      any(a["field"] == "exit" and a["rule"] == "eq_int:0" for a in spec0)
      and any(a["field"] == "stdout" for a in spec0))
spec1 = stage5_loop._smoke_spec(_Obs(exit_code=1, stderr=b"no --version"))
check("cli nonzero banner does NOT pin exact exit (fair)", not any(a["field"] == "exit" for a in spec1))
check("cli nonzero banner still pins stderr nonempty", any(a["field"] == "stderr" for a in spec1))
specS = stage5_loop._smoke_spec(_Obs(http=[{"status": 200, "body": "ok"}]))
check("service smoke pins http:0:status", specS == [{"field": "http:0:status", "class": "invariant", "rule": "eq_int:200"}])

# ---- 3) pytest_emit partitions + counts -------------------------------------
src = pathlib.Path(tempfile.mkdtemp())
(src / "05_tests").mkdir()
(src / "05_smoke").mkdir()
(src / "05_tests" / "func1.json").write_text(json.dumps({"id": "func1", "modules": ["M1"],
    "scenario_type": "cli", "input": {"argv": ["x"]},
    "assertions": [{"field": "stdout", "class": "invariant", "rule": "nonempty"}]}), encoding="utf-8")
(src / "05_tests" / "sec1.json").write_text(json.dumps({"id": "sec1", "modules": ["M1"],
    "scenario_type": "cli", "security_metric": "SEC-6", "input": {"argv": ["../../etc/passwd"]},
    "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:2"}]}), encoding="utf-8")
(src / "05_smoke" / "smoke_0_help.json").write_text(json.dumps({"id": "smoke_0_help", "modules": ["SMOKE"],
    "scenario_type": "cli", "kind": "smoke", "smoke": True, "input": {"argv": ["--help"]},
    "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:0"}]}), encoding="utf-8")
grader = pathlib.Path(tempfile.mkdtemp()) / "grader"
rep = pytest_emit.emit(src, grader, "cli", {})
check("emit returns dict", isinstance(rep, dict))
check("emit counts n_tests=2", rep.get("n_tests") == 2)
check("emit counts n_security=1", rep.get("n_security") == 1)
check("emit security_by_metric SEC-6", rep.get("security_by_metric") == {"SEC-6": 1})
check("emit counts n_smoke=1", rep.get("n_smoke") == 1)
check("grader has test_smoke.py", (grader / "test_smoke.py").exists())
check("grader cases has all 3 (2 tests + 1 smoke)", len(list((grader / "cases").glob("*.json"))) == 3)
check("test_blackbox filters out smoke", "not c.get(\"smoke\")" in (grader / "test_blackbox.py").read_text(encoding="utf-8"))
check("test_smoke selects smoke", '.get("smoke")' in (grader / "test_smoke.py").read_text(encoding="utf-8"))
check("conftest reports security NFR", "security NFR pass-rate" in (grader / "conftest.py").read_text(encoding="utf-8"))
check("conftest skips SMOKE module", 'm == "SMOKE"' in (grader / "conftest.py").read_text(encoding="utf-8"))

# ---- 4) full stage8 render surfaces security + smoke ------------------------
ro2 = pathlib.Path(tempfile.mkdtemp())
def wr(p, obj): (ro2 / p).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
wr("nfr-metrics.json", {"metrics": [{"id": "SEC5", "name": "SQL注入防护", "dimension": "SEC", "kind": "runtime", "scoring": "ratio100", "desc": "恶意输入全部被安全处理。"},
   {"id": "MTN1", "name": "无超大单文件", "dimension": "MTN", "kind": "static", "scoring": "binary", "desc": "无 >1000 LOC 文件。"}]})
wr("01_repo-model.json", {"repo_id": "owner-tool", "scenario_type": "cli", "language": "python",
   "rewritable_languages": ["go"], "candidate_brief": "A command-line utility that processes documents."})
wr("02_cli-contract.json", {"contract_type": "cli", "binary": "tool", "usage": "tool FILE",
   "exit_codes": {"0": "ok", "2": "error"}})
wr("03_modules.json", {"modules": [{"id": "M1", "name": "Process", "user_value": "v"}]})
wr("03_user-stories.json", {"stories": [{"id": "S1", "modules": ["M1"],
   "prose": {"actor": "u", "precondition": "p", "trigger": "t", "expected": "e"}, "code": ["app x"]}]})
wr("04_nfr-labels.json", {"labels": [{"metric_id": "SEC5", "applies": True}, {"metric_id": "MTN1", "applies": True}],
   "applicable": ["SEC5", "MTN1"]})
(ro2 / "05_tests").mkdir()
(ro2 / "05_tests" / "sec1.json").write_text(json.dumps({"id": "sec1", "modules": ["M1"],
   "scenario_type": "cli", "security_metric": "SEC5", "input": {"argv": ["../x"]},
   "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:2"}]}), encoding="utf-8")
(ro2 / "05_smoke").mkdir()
(ro2 / "05_smoke" / "smoke_0_help.json").write_text(json.dumps({"id": "smoke_0_help", "modules": ["SMOKE"],
   "scenario_type": "cli", "kind": "smoke", "smoke": True, "input": {"argv": ["--help"]},
   "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:0"}]}), encoding="utf-8")
rep2 = stage8_package.run(ro2, {"scenario_type": "cli"})
check("stage8 report security_tests=1", rep2.get("security_tests") == 1)
check("stage8 report smoke_tests=1", rep2.get("smoke_tests") == 1)
nfr_md = (ro2 / "07_exam" / "candidate" / "非功能需求.md").read_text(encoding="utf-8")
check("non-functional doc has 安全性专项测试 section", "安全性专项测试" in nfr_md)
check("non-functional doc lists applicable metric", "SEC5" in nfr_md or "SQL注入防护" in nfr_md)
check("non-functional doc lists static MTN metric too", "MTN1" in nfr_md)

# ---- 5) gate content-coverage excludes security/smoke cases -----------------
import gates
ro3 = pathlib.Path(tempfile.mkdtemp())
(ro3 / "05_tests").mkdir()
# 1 functional case pinning stdout (strong) + 3 exit-only security cases. If security counted in the
# denominator the ratio would be 1/4=0.25 (<0.50 -> gate fail); excluding them it must be 1/1=1.0.
(ro3 / "05_tests" / "f1.json").write_text(json.dumps({"id": "f1", "modules": ["M1"],
    "assertions": [{"field": "stdout", "class": "exact", "value": {"utf8": "x"}}]}), encoding="utf-8")
for k in range(3):
    (ro3 / "05_tests" / f"s{k}.json").write_text(json.dumps({"id": f"s{k}", "modules": ["M1"],
        "security_metric": "SEC-1", "assertions": [{"field": "exit", "class": "invariant", "rule": "eq_int:2"}]}),
        encoding="utf-8")
ratio = gates._content_coverage_ratio(ro3)
check("content-coverage excludes exit-only security cases (ratio=1.0)", abs(ratio - 1.0) < 1e-9)

shutil.rmtree(ro, ignore_errors=True); shutil.rmtree(src, ignore_errors=True)
shutil.rmtree(ro2, ignore_errors=True); shutil.rmtree(ro3, ignore_errors=True)
print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
