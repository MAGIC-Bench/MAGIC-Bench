"""NFR scoring (Phase C) — pure scoring logic.

Given a candidate RUN REPORT (produced by running the candidate over the suite + applicable run-modes)
and STATIC codex results, produce a TWO-dimension result that is NOT aggregated into a single total:

    { "build_ok": bool,
      "功能分":   <0..1 functional test pass rate>,
      "nfr_by_dimension": { "<dim>": { "<metric_id>": 1|0|None, ... }, ... } }

Hard gate (req): if the candidate did not build / its smoke failed (build_ok=False) -> 功能分=0 AND every
NFR metric=0. Each NFR metric is 0/1 per docs/nfr-metrics-table.md; ratio100 metrics (SEC1/4/5) need 100%.
A metric scores None when it is applicable but this run produced no data to score it (e.g. latency not
instrumented, or no security cases were generated) -- surfaced honestly rather than silently passed.

RUN REPORT contract (the grader-side runner fills this):
  { "build_ok": bool,
    "total_time_s": float,                       # wall time of the functional run
    "cases": [ { "id", "passed": bool, "security_metric": str|None, "smoke": bool,
                 "latency_s": float, "peak_mem_mb": float|None,
                 "crashed": bool, "timed_out": bool, "oom": bool } ],
    "modes": { "RLY5": {"passed": bool}, "RLY1": {...}, "CMP2": {...}, ... } }   # applicable run-modes
"""
from __future__ import annotations

DEFAULT_THRESHOLDS = {
    "perf4_pass_rate": 0.7,    # PERF4: >= this fraction of functional cases correct
    "perf4_time_s": 600.0,     # PERF4: within this wall time
    "perf2_tar": 5.0,          # PERF2: tail amplification L99/L50 <= this
    "perf3_mem_mb": 2048.0,    # PERF3: peak RSS <= this
}

RATIO100 = {"SEC1", "SEC4", "SEC5"}   # 100% of the metric's security cases must pass


def _percentile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _functional(cases):
    return [c for c in cases if not c.get("security_metric") and not c.get("smoke")]


def _security_for(cases, mid):
    return [c for c in cases if c.get("security_metric") == mid]


def _no_runtime_fail(cases):
    return not any(c.get("crashed") or c.get("timed_out") or c.get("oom") for c in cases)


def _score_metric(mid, report, thr, static_results):
    """1 / 0 / None (None = applicable but not measurable this run)."""
    cases = report.get("cases", [])
    func = _functional(cases)
    # --- PTB1 build gate (reached only when build_ok=True, since failure zeros upstream) ---
    if mid == "PTB1":                                    # standard build passed
        return 1 if report.get("build_ok", True) else 0
    # --- PERF (runtime, derived from the single rich run) ---
    if mid == "PERF1":                                   # no crash / OOM / timeout
        return 1 if _no_runtime_fail(cases) else 0
    if mid == "PERF4":                                   # timed correctness gate
        rate = (sum(1 for c in func if c.get("passed")) / len(func)) if func else 0.0
        ok = (rate >= thr["perf4_pass_rate"]
              and report.get("total_time_s", 0.0) <= thr["perf4_time_s"]
              and _no_runtime_fail(cases))
        return 1 if ok else 0
    if mid == "PERF2":                                   # tail latency TAR = L99 / max(L50, .001)
        lat = [c["latency_s"] for c in func if isinstance(c.get("latency_s"), (int, float))]
        if not lat:
            return None
        tar = _percentile(lat, 0.99) / max(_percentile(lat, 0.50), 0.001)
        return 1 if tar <= thr["perf2_tar"] else 0
    if mid == "PERF3":                                   # peak memory
        mems = [c["peak_mem_mb"] for c in cases if isinstance(c.get("peak_mem_mb"), (int, float))]
        if not mems:
            return None
        return 1 if max(mems) <= thr["perf3_mem_mb"] else 0
    # --- SEC1/4/5 (runtime, ratio100: ALL of that metric's security cases must pass) ---
    if mid in RATIO100:
        sc = _security_for(cases, mid)
        if not sc:
            return None
        return 1 if all(c.get("passed") for c in sc) else 0
    # --- RLY* / CMP2 (runtime modes the grader ran) ---
    modes = report.get("modes", {})
    if mid in modes:
        return 1 if modes[mid].get("passed") else 0
    # --- static metrics (codex 0/1) ---
    if mid in static_results:
        return 1 if static_results[mid] else 0
    return None                                          # applicable but no data this run


def compute_scores(report, applicable, static_results=None, thresholds=None):
    """report: run report dict. applicable: [{metric_id, dimension, kind, scoring}]. Returns the
    two-dimension score; build failure zeros everything."""
    thr = dict(DEFAULT_THRESHOLDS)
    thr.update(thresholds or {})
    static_results = static_results or {}
    build_ok = bool(report.get("build_ok", True))
    func = _functional(report.get("cases", []))

    functional = 0.0
    if build_ok and func:
        functional = sum(1 for c in func if c.get("passed")) / len(func)

    by_dim = {}
    for m in applicable:
        mid = m.get("metric_id")
        dim = m.get("dimension", "?")
        score = 0 if not build_ok else _score_metric(mid, report, thr, static_results)
        by_dim.setdefault(dim, {})[mid] = score
    return {"build_ok": build_ok, "功能分": round(functional, 4), "nfr_by_dimension": by_dim}
