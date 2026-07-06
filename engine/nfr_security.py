"""Pick the security NFR metrics that warrant EXTRA black-box security test cases (data augmentation).

Driven by Stage-4 labels (`04_nfr-labels.json`): of the three behavior-testable security metrics
SEC1 (未授权读阻断) / SEC4 (未授权写阻断) / SEC5 (SQL注入防护), generate tagged security test cases for
whichever the labeler marked `applies=true` for this repo. The other security metrics (SEC2/3/6 — no
hardcoded secret / encrypted storage / audit log) are STATIC (scored by reading the candidate's source),
not black-box input cases, so they are excluded here.
"""
from __future__ import annotations

import json
import pathlib

# the only behavior-testable (black-box) security metrics, with their test-design kind
SECURITY_KINDS = {
    "SEC1": "unauthorized_access",   # 未授权读阻断
    "SEC4": "unauthorized_modify",   # 未授权写阻断
    "SEC5": "malicious_input",       # SQL注入 / 恶意输入防护
}


def _metrics_index(repo_out):
    """id -> {name, desc} from nfr-metrics.json copied into the repo out dir."""
    p = pathlib.Path(repo_out) / "nfr-metrics.json"
    idx = {}
    if p.exists():
        try:
            for m in json.loads(p.read_text(encoding="utf-8")).get("metrics", []):
                idx[str(m.get("id"))] = {"name": str(m.get("name", "")), "desc": str(m.get("desc", ""))}
        except Exception:
            pass
    return idx


def applicable_metrics(repo_out):
    """Set of metric_ids the Stage-4 labeler marked applies=true for this repo (04_nfr-labels.json)."""
    repo_out = pathlib.Path(repo_out)
    lp = repo_out / "04_nfr-labels.json"
    if not lp.exists():
        return set()
    try:
        labels = json.loads(lp.read_text(encoding="utf-8"))
    except Exception:
        return set()
    app = {x for x in (labels.get("applicable") or []) if isinstance(x, str)}
    for lab in (labels.get("labels") or []):
        if isinstance(lab, dict) and lab.get("applies") and isinstance(lab.get("metric_id"), str):
            app.add(lab["metric_id"])
    return app


def pick_security_metrics(repo_out):
    """Return [{metric_id, name, kind}] for the behavior-testable security metrics (SEC1/SEC4/SEC5)
    the Stage-4 labeler marked applies=true. Empty list => no security-test augmentation for this repo."""
    app = applicable_metrics(repo_out)
    idx = _metrics_index(repo_out)
    return [{"metric_id": mid, "name": idx.get(mid, {}).get("name", mid), "kind": kind}
            for mid, kind in SECURITY_KINDS.items() if mid in app]
