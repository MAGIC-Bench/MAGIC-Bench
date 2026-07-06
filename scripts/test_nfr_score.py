"""Unit-test the pure NFR scoring logic (engine/nfr_score.py)."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import nfr_score

fails = []
def chk(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

APP = [
    {"metric_id": "PERF4", "dimension": "PERF"}, {"metric_id": "PERF1", "dimension": "PERF"},
    {"metric_id": "PERF2", "dimension": "PERF"}, {"metric_id": "PERF3", "dimension": "PERF"},
    {"metric_id": "SEC5", "dimension": "SEC"}, {"metric_id": "RLY5", "dimension": "RLY"},
    {"metric_id": "MTN1", "dimension": "MTN"}, {"metric_id": "SEC1", "dimension": "SEC"},
]

def fcase(passed, **kw):
    d = {"id": "x", "passed": passed, "latency_s": 0.1, "peak_mem_mb": 100.0,
         "crashed": False, "timed_out": False, "oom": False}
    d.update(kw); return d

# --- build failure zeros everything ---
r = nfr_score.compute_scores({"build_ok": False, "cases": [fcase(True)]}, APP)
chk("build fail -> 功能分 0", r["功能分"] == 0.0)
chk("build fail -> every NFR metric 0", all(v == 0 for dim in r["nfr_by_dimension"].values() for v in dim.values()))

# --- functional pass rate ---
cases = [fcase(True), fcase(True), fcase(True), fcase(False),
         {"id": "s", "passed": True, "security_metric": "SEC5", "latency_s": 0.1, "crashed": False, "timed_out": False, "oom": False},
         {"id": "sm", "passed": True, "smoke": True, "latency_s": 0.1, "crashed": False, "timed_out": False, "oom": False}]
r = nfr_score.compute_scores({"build_ok": True, "total_time_s": 10.0, "cases": cases,
                              "modes": {"RLY5": {"passed": True}}},
                             APP, static_results={"MTN1": 1})
chk("功能分 = 3/4 functional (excludes security+smoke)", r["功能分"] == 0.75)
chk("PERF4 = 1 (75%>=70%, <600s, no fail)", r["nfr_by_dimension"]["PERF"]["PERF4"] == 1)
chk("PERF1 = 1 (no crash)", r["nfr_by_dimension"]["PERF"]["PERF1"] == 1)
chk("SEC5 = 1 (its 1 case passed)", r["nfr_by_dimension"]["SEC"]["SEC5"] == 1)
chk("RLY5 = 1 (from modes)", r["nfr_by_dimension"]["RLY"]["RLY5"] == 1)
chk("MTN1 = 1 (static codex)", r["nfr_by_dimension"]["MTN"]["MTN1"] == 1)
chk("SEC1 = None (applicable but no SEC1 cases)", r["nfr_by_dimension"]["SEC"]["SEC1"] is None)
chk("PERF2 = 1 (flat latency)", r["nfr_by_dimension"]["PERF"]["PERF2"] == 1)
chk("PERF3 = 1 (mem under 2GB)", r["nfr_by_dimension"]["PERF"]["PERF3"] == 1)

# --- PERF4 fails under 70% ---
r2 = nfr_score.compute_scores({"build_ok": True, "total_time_s": 10.0,
                               "cases": [fcase(True), fcase(False), fcase(False)]}, APP)
chk("PERF4 = 0 (33% < 70%)", r2["nfr_by_dimension"]["PERF"]["PERF4"] == 0)

# --- a crash zeros PERF1 + PERF4 ---
r3 = nfr_score.compute_scores({"build_ok": True, "total_time_s": 10.0,
                               "cases": [fcase(True), fcase(True, crashed=True)]}, APP)
chk("PERF1 = 0 (a crash)", r3["nfr_by_dimension"]["PERF"]["PERF1"] == 0)
chk("PERF4 = 0 (runtime failure)", r3["nfr_by_dimension"]["PERF"]["PERF4"] == 0)

# --- SEC5 needs 100% (ratio100) ---
r4 = nfr_score.compute_scores({"build_ok": True, "total_time_s": 5.0, "cases": [
    {"id": "a", "passed": True, "security_metric": "SEC5", "crashed": False, "timed_out": False, "oom": False},
    {"id": "b", "passed": False, "security_metric": "SEC5", "crashed": False, "timed_out": False, "oom": False}]},
    [{"metric_id": "SEC5", "dimension": "SEC"}])
chk("SEC5 = 0 (one security case failed -> not 100%)", r4["nfr_by_dimension"]["SEC"]["SEC5"] == 0)

# --- PERF2 fails on a tail spike ---
spike = [fcase(True, latency_s=0.1) for _ in range(98)] + [fcase(True, latency_s=10.0), fcase(True, latency_s=20.0)]
r5 = nfr_score.compute_scores({"build_ok": True, "total_time_s": 30.0, "cases": spike},
                              [{"metric_id": "PERF2", "dimension": "PERF"}])
chk("PERF2 = 0 (huge tail amplification)", r5["nfr_by_dimension"]["PERF"]["PERF2"] == 0)

print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
