"""Stage gates: schema validation + per-stage business rules.

A stage's artifact must (a) validate against its JSON Schema and (b) pass the
business gate before the orchestrator advances. Failing a gate stops that repo.
"""
from __future__ import annotations

import json
import pathlib

import deident

try:
    import jsonschema
    _HAVE_JSONSCHEMA = True
except Exception:
    _HAVE_JSONSCHEMA = False

SCHEMAS = pathlib.Path(__file__).resolve().parent.parent / "schemas"


def validate_schema(obj, schema_name: str):
    schema_path = SCHEMAS / schema_name
    if not schema_path.exists():
        return True, f"(no schema {schema_name}, skipped)"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if _HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(obj, schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"schema: {e.message} at {list(e.path)}"
    # minimal fallback: top-level required keys only
    for key in schema.get("required", []):
        if isinstance(obj, dict) and key not in obj:
            return False, f"missing required key: {key}"
    return True, "(minimal check; install jsonschema for full validation)"


_CONTENT_FIELDS = ("stdout", "stderr", "file:")


def _content_coverage_ratio(repo_out: pathlib.Path):
    """Fraction of cases that pin a CONTENT field (stdout/stderr/file) with a real VALUE check:
    exact / normalized, or an invariant that checks content (regex / eq_int / valid_json). `exit` and
    weak/absent checks (ignored / nonempty / empty) do NOT count. None if there are no cases.
    Used by gate_stage5 (exit-only suites too weak) AND gate_stage6 (repair must not gut the exam)."""
    tests_dir = repo_out / "05_tests"
    cases = list(tests_dir.rglob("*.json")) if tests_dir.exists() else []
    if not cases:
        return None
    strong = total = 0
    for fp in cases:
        try:
            c = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        # ratio measures FUNCTIONAL output coverage; security cases (req 2.7) are spec-mandated to be
        # exit-only/refusal probes and would mechanically dilute it -> exclude them (and any smoke).
        if c.get("security_metric") or c.get("smoke"):
            continue
        total += 1
        for a in c.get("assertions", []):
            if not str(a.get("field", "")).startswith(_CONTENT_FIELDS):
                continue
            cls, rule = a.get("class"), str(a.get("rule", ""))
            if cls in ("exact", "normalized") or (cls == "invariant" and (
                    rule.startswith("regex:") or rule.startswith("eq_int:") or rule == "valid_json")):
                strong += 1
                break
    return strong / total if total else None


# ---- per-stage business gates ------------------------------------------------

def gate_stage1(repo_out: pathlib.Path):
    m = json.loads((repo_out / "01_repo-model.json").read_text(encoding="utf-8"))
    if m.get("scenario_type") not in ("cli", "service", "pipeline"):
        return False, "scenario_type must be cli|service|pipeline"
    if not m.get("public_surface"):
        return False, "empty public_surface"
    # candidate_brief: the de-identified business description shown to the candidate (req 2.1).
    brief = str(m.get("candidate_brief", "")).strip()
    if not brief:
        return False, "missing candidate_brief (de-identified business description for the candidate)"
    # anti-cheat: the brief must not contain the repo-name/owner tokens (incl. short names jq/bat/fd).
    leak = deident.leak_tokens(brief, deident.identity_tokens(m.get("repo_id", "")))
    if leak:
        return False, f"candidate_brief leaks repo-name token(s) {leak} -- must be de-identified"
    return True, None


def gate_stage3(repo_out: pathlib.Path):
    """No orphan op; every module is user-facing (user_value) with >=1 story; every story is
    well-formed (prose 4-fields + non-empty code). Enforces req 2.3/2.4 beyond schema."""
    modules = json.loads((repo_out / "03_modules.json").read_text(encoding="utf-8"))
    stories = json.loads((repo_out / "03_user-stories.json").read_text(encoding="utf-8")).get("stories", [])
    mod_list = modules.get("modules", [])
    mod_ids = {m["id"] for m in mod_list}
    # 2.3: modules are user-facing capabilities -> user_value required & non-empty
    no_value = [m.get("id", "?") for m in mod_list if not str(m.get("user_value", "")).strip()]
    if no_value:
        return False, f"modules missing user_value (must be user-facing capabilities): {no_value}"
    storied = {s_m for s in stories for s_m in s.get("modules", [])}
    missing = mod_ids - storied
    if missing:
        return False, f"modules without a user story: {sorted(missing)}"
    # 2.4: each story must carry the full prose format + a non-empty executable code block
    bad = []
    for s in stories:
        pr = s.get("prose", {})
        if not all(str(pr.get(k, "")).strip() for k in ("actor", "precondition", "trigger", "expected")):
            bad.append(f"{s.get('id', '?')}:prose")
        elif not [c for c in (s.get("code") or []) if str(c).strip()]:
            bad.append(f"{s.get('id', '?')}:code")
    if bad:
        return False, f"user stories missing required format (prose 4-fields + non-empty code): {bad}"
    return True, None


def gate_stage5(repo_out: pathlib.Path, quota: int = 20):
    """Every test tagged to >=1 module; every module reaches `quota` OR is needs_review."""
    led = json.loads((repo_out / "05_coverage-ledger.json").read_text(encoding="utf-8"))
    summary = led["summary"]
    per_module = summary.get("per_module", {})
    needs_review = set(summary.get("needs_review", []))
    untagged = summary.get("untagged_tests", 0)
    if untagged:
        return False, f"{untagged} untagged testcases"
    short = [m for m, c in per_module.items() if c < quota and m not in needs_review]
    if short:
        return False, f"modules below quota {quota} and not flagged needs_review: " \
                      + ", ".join(f"{m}={per_module[m]}" for m in short)
    # content-field coverage: exit-only assertions are too weak (a garbage-stdout impl with the right
    # exit code would still pass). Require >=50% of tests to pin a CONTENT field with a value check.
    ratio = _content_coverage_ratio(repo_out)
    if ratio is not None and ratio < 0.50:
        return False, (f"only {ratio:.0%} of tests pin a content field (stdout/stderr/file) with a "
                       f"value check (need >=50%) -- exit-only assertions are too weak")
    return True, None


def gate_stage7(repo_out: pathlib.Path, max_drop: float = 0.05):
    """Exam soundness. stage7 drops cases the ORIGINAL fails on its own golden (bad/unstable
    golden); after that the survivors must pass ~100%, and not too many cases were dropped.
    A high drop-rate means the original can't pass its own exam (poisoned golden) -> fail the
    repo instead of shipping a bad exam (e.g. cisco: high-water 0.89 was wrongly marked ok)."""
    rep = json.loads((repo_out / "07_verify.json").read_text(encoding="utf-8"))
    hw = rep.get("high_water", {})
    rate, drop_rate, total = hw.get("rate", 0.0), hw.get("drop_rate", 0.0), hw.get("total", 0)
    if total < 1:
        return False, "stage7: no surviving test cases"
    if rate < 1.0:
        return False, f"stage7: high-water {rate:.0%} < 100% even after dropping bad-golden cases"
    if drop_rate > max_drop:
        return False, (f"stage7: dropped {drop_rate:.0%} of cases as bad golden (> {max_drop:.0%}) "
                       f"-- original fails its own golden too often, exam unsound")
    return True, None


def gate_stage6(repo_out: pathlib.Path):
    """Adversarial review is a HARD gate, not a report: open_critical MUST be 0 to ship (req 2), AND
    the review->repair loop must not have GUTTED the exam to get there -- anti-gaming: content coverage
    must still hold >=50% (repair can't just mark everything `ignored`). stage6 flags over-constrained
    exact, frozen original-bugs vs contract, white-box leakage, the program name passed as argv, etc."""
    adv = json.loads((repo_out / "06_adversarial.json").read_text(encoding="utf-8"))
    oc = adv.get("open_critical", 0) or 0
    if oc > 0:
        fs = adv.get("findings", [])
        sample = "; ".join(str(f.get("issue", f))[:90] for f in fs[:3]) if isinstance(fs, list) else ""
        return False, f"stage6: open_critical={oc} (must be 0) -- shipping-blockers found: {sample}"
    ratio = _content_coverage_ratio(repo_out)
    if ratio is not None and ratio < 0.50:
        return False, (f"stage6: after repair only {ratio:.0%} of tests still pin a content field "
                       f"(need >=50%) -- repair over-relaxed assertions (anti-gaming guard)")
    return True, None


GATES = {1: gate_stage1, 3: gate_stage3, 5: gate_stage5, 6: gate_stage6, 7: gate_stage7}


def business_gate(stage: int, repo_out: pathlib.Path, config: dict | None = None):
    fn = GATES.get(stage)
    if fn is None:
        return True, None
    try:
        if stage == 5:                       # forward the configured quota (req 2.8: don't hardcode 20)
            return fn(repo_out, quota=(config or {}).get("quota", 20))
        if stage == 7:                       # allow per-repo drop_threshold override in manifest
            return fn(repo_out, max_drop=(config or {}).get("drop_threshold", 0.05))
        return fn(repo_out)
    except FileNotFoundError as e:
        return False, f"missing artifact: {e}"
