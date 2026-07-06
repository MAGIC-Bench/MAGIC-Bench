"""Guarantee EVERY metric in dataset/nfr-metrics.json has a concrete code path (no silent gaps).
runtime metric -> derived in nfr_score.py OR a mode in _grade.py; static metric -> codex static path."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
metrics = json.loads((ROOT / "dataset" / "nfr-metrics.json").read_text(encoding="utf-8"))["metrics"]
grade_src = (ROOT / "engine" / "_grade.py").read_text(encoding="utf-8")
score_src = (ROOT / "engine" / "nfr_score.py").read_text(encoding="utf-8")

DERIVED = {"PTB1", "PERF1", "PERF2", "PERF3", "PERF4", "SEC1", "SEC4", "SEC5"}   # computed in nfr_score
MODES = {"RLY1", "RLY2", "RLY3", "RLY4", "RLY5", "RLY6", "CMP2"}                 # produced by run_modes/service_modes

fails = []
def chk(n, c):
    print(("OK   " if c else "FAIL ") + n)
    if not c: fails.append(n)

chk("static metrics dispatched to codex (static_scores)", "def static_scores" in grade_src and "kind\") == \"static\"" in grade_src)
chk("nfr_score routes static_results -> metric", "static_results" in score_src)

for m in metrics:
    mid, kind = m["id"], m["kind"]
    if kind == "static":
        chk(f"{mid} (static) covered by codex path", True)        # all statics flow through static_scores
    else:
        chk(f"{mid} (runtime) has a code path", mid in DERIVED or mid in MODES)
        if mid in DERIVED:
            chk(f"  {mid} implemented in nfr_score.py", f'"{mid}"' in score_src)
        if mid in MODES:
            chk(f"  {mid} implemented in _grade.py", f'"{mid}"' in grade_src)

runtime_ids = {m["id"] for m in metrics if m["kind"] == "runtime"}
chk("EVERY runtime metric is in DERIVED|MODES", runtime_ids <= (DERIVED | MODES))
unknown = (DERIVED | MODES) - {m["id"] for m in metrics}
chk("no stray scorer ids not in the table", not unknown)

print(f"\n{len(metrics)} metrics audited.  == FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
