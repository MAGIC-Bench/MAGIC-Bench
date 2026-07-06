"""Per-repo x per-stage driver: Stage 0-7, gates, resumable (STATUS.json).

Each model stage's artifact is schema-validated + business-gated before advancing.
A failed gate stops that repo and records the reason; stages 6/7 are human-review
gates in production. Runs one repo here; batch = a process pool over many configs.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
for _d in ("engine", "agent", "stages"):
    sys.path.insert(0, str(ROOT / _d))

import config as cfgmod
import gates
import stage0_ingest
import stage5_loop
import stage7_verify
import stage8_package
import agent_stages

STAGES = [0, 1, 2, 3, 4, 5, 6, 7, 8]
HUMAN_GATES = {6, 7}
ARTIFACT_SCHEMA = {1: [("01_repo-model.json", "repo-model.schema.json")],
                   3: [("03_modules.json", "modules.schema.json"),
                       ("03_user-stories.json", "user-stories.schema.json")],
                   4: [("04_nfr-labels.json", "nfr-labels.schema.json")]}


def _status_path(repo_out):
    return repo_out / "STATUS.json"


def load_status(repo_out):
    p = _status_path(repo_out)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_status(repo_out, status):
    _status_path(repo_out).write_text(json.dumps(status, indent=2), encoding="utf-8")


_VALID_NORM = {"crlf_lf", "strip", "rstrip_eol", "lines_sorted", "json_canonical"}
_VALID_INV = {"nonempty", "empty", "valid_json"}


def _malformed_findings(repo_out):
    """Mechanical check: cases whose assertions use an INVALID class/rule keyword (e.g. a repair invented
    a rule like `rfc6902_transforms:...`). Returned as synthetic CRITICAL findings so the repair loop
    fixes them -- otherwise the stage7 grader cannot run the assertion."""
    out = []
    for fp in sorted((pathlib.Path(repo_out) / "05_tests").glob("*.json")):
        try:
            c = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        for a in c.get("assertions", []):
            cls, rule = a.get("class"), a.get("rule")
            bad = None
            if cls not in ("exact", "normalized", "invariant", "ignored"):
                bad = f"class {cls!r}"
            elif cls == "normalized" and not (rule in _VALID_NORM or str(rule).startswith("regex_extract:")):
                bad = f"normalized rule {rule!r}"
            elif cls == "invariant" and not (rule in _VALID_INV or str(rule).startswith(("regex:", "eq_int:"))):
                bad = f"invariant rule {rule!r}"
            if bad:
                out.append({"test_id": c.get("id"), "severity": "critical",
                            "issue": f"malformed assertion ({bad}) on field {a.get('field')!r} -- not a valid "
                                     f"class/rule keyword; the grader cannot run it",
                            "fix": "replace with a VALID assertion (invariant rule = nonempty|empty|valid_json|"
                                   "regex:<re>|eq_int:<n>; normalized rule = crlf_lf|strip|rstrip_eol|"
                                   "lines_sorted|json_canonical|regex_extract:<re>)"})
                break
    return out


def _run_stage6(repo_src, repo_out, config, agent_mode):
    """Adversarial review -> repair -> re-review loop (mirrors the stage0 build-repair loop). Round 0 is
    a FULL independent review; later rounds RE-REVIEW ONLY the just-repaired cases (scoped, cheaper --
    the rest were already cleared). Repair edits ONLY flagged 05_tests cases. gate_stage6 then enforces
    open_critical==0 + content coverage. Stub mode reviews once (its stub is open_critical=0)."""
    repo_out = pathlib.Path(repo_out)
    max_repairs = config.get("max_repairs", 5)
    oc, attempt, focus = 0, 0, None
    for attempt in range(max_repairs + 1):
        agent_stages.adversarial_review(repo_src, repo_out, config, agent_mode, focus_ids=focus)
        adv = json.loads((repo_out / "06_adversarial.json").read_text(encoding="utf-8"))
        mal = _malformed_findings(repo_out)                      # mechanical: invalid class/rule -> repair it
        findings = adv.get("findings", []) + mal
        oc = (adv.get("open_critical", 0) or 0) + len(mal)
        adv["open_critical"], adv["repair_attempts"] = oc, attempt
        if mal:
            adv["malformed"] = [m["test_id"] for m in mal]
        (repo_out / "06_adversarial.json").write_text(
            json.dumps(adv, indent=2, ensure_ascii=False), encoding="utf-8")
        if oc == 0 or attempt == max_repairs or agent_mode == "stub":
            break
        crit = [f for f in findings if f.get("severity") == "critical"]
        # next round: re-review ONLY the cases we're about to repair (scoped). If any finding targets a
        # pattern/suite (can't enumerate), fall back to a FULL re-review for safety.
        ids, scoped = set(), True
        for f in crit:
            tid = str(f.get("test_id", "")).strip()
            if not tid or tid.startswith(("suite:", "ALL")):
                scoped = False
                break
            ids.update(p.strip() for p in tid.split(",") if p.strip())
        focus = sorted(ids) if (scoped and ids) else None
        print(f"   stage6: open_critical={oc} -> repair round {attempt + 1}/{max_repairs}"
              + (f" (scoped re-review: {len(focus)} cases)" if focus else " (full re-review)"))
        agent_stages.repair_stage6(repo_src, repo_out, config, agent_mode, crit)
    print(f"   stage6: open_critical={oc} after {attempt} repair round(s)")
    return True, None


def run_stage(stage, repo_id, repo_src, config, repo_out, agent_mode):
    if stage == 0:
        return stage0_ingest.run(repo_id, repo_src, config, repo_out, agent_mode)
    if stage in (1, 2, 3, 4):
        agent_stages.model_stage(stage, repo_src, repo_out, config, agent_mode)
        return True, None
    if stage == 6:
        return _run_stage6(repo_src, repo_out, config, agent_mode)
    if stage == 5:
        provider = agent_stages.draft_provider(repo_src, repo_out, config, agent_mode)
        summary = stage5_loop.run(repo_out, config, provider, quota=config.get("quota", 20),
                                  max_rounds=config.get("max_rounds", 3))
        print(f"   stage5: {summary['tests_emitted']} tests | per-module={json.dumps(summary['per_module'])}"
              f" | needs_review={summary['needs_review']}"
              + (f" | security={summary['security_tests']}{json.dumps(summary['security_by_metric'])}"
                 if summary.get('security_tests') else "")
              + (f" | smoke={summary['smoke_tests']}" if summary.get('smoke_tests') else "")
              + (f" | cov={summary['pct_statements']}%" if summary.get('pct_statements') else ""))
        return True, None
    if stage == 7:
        rep = stage7_verify.run(repo_out, repo_src, config, str(ROOT / "bin"))
        hw = rep["high_water"]
        print(f"   stage7: high-water {hw['passed']}/{hw['total']} ({hw['rate']:.1%})"
              + (f" | dropped {hw['dropped']} bad-golden ({hw['drop_rate']:.0%})" if hw.get('dropped') else ""))
        return True, None
    if stage == 8:
        rep = stage8_package.run(repo_out, config)
        print(f"   stage8: grader={rep['grader_tests']} tests · gen-lang={rep['generation_language']}"
              f" · applicable_metrics={rep['applicable_metrics']} · rewritable={rep['rewritable_languages']}"
              + (f" · security={rep['security_tests']}{json.dumps(rep['security_by_metric'])}"
                 if rep.get('security_tests') else "")
              + (f" · smoke={rep['smoke_tests']}" if rep.get('smoke_tests') else ""))
        return True, None
    return False, f"unknown stage {stage}"


def check_gate(stage, repo_out, config=None):
    for art, schema in ARTIFACT_SCHEMA.get(stage, []):
        p = repo_out / art
        if p.exists():
            ok, msg = gates.validate_schema(json.loads(p.read_text(encoding="utf-8")), schema)
            if not ok:
                return False, f"{art}: {msg}"
    return gates.business_gate(stage, repo_out, config)


def _merge_runtime(config, repo_out):
    """After Stage 0, merge the agent-discovered runtime (service/pipeline/dependencies)
    from 00_runtime.json into config so Stage 5/7 + grading can drive the image. Agent-built
    docker images aren't coverage-instrumented -> coverage falls back to 'none' (the Stage 5
    loop then fills by module quota instead of coverage hints)."""
    p = pathlib.Path(repo_out) / "00_runtime.json"
    if not p.exists():
        return
    try:
        rt = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    for k in ("service", "pipeline", "dependencies", "launch", "smoke"):
        if rt.get(k):
            config[k] = rt[k]                              # launch: agent-discovered local run command
    if (config.get("runtime") or {}).get("mode") == "docker":
        config["coverage"] = "none"


def run_repo_config(config, agent_mode="stub", frm=0, to=7):
    repo_id = config["repo_id"]
    repo_src = config["src"]
    repo_out = pathlib.Path(config.get("out_dir") or (ROOT / "out" / repo_id))
    repo_out.mkdir(parents=True, exist_ok=True)
    _mt = ROOT / "dataset" / "nfr-metrics.json"        # feed the NFR metrics table to Stage 4 (labeling)
    if _mt.exists() and not (repo_out / "nfr-metrics.json").exists():
        shutil.copy(_mt, repo_out / "nfr-metrics.json")
    status = load_status(repo_out)
    if (repo_out / "00_runtime.json").exists():   # RESUME: stage 0 may be skipped this run, so the
        _merge_runtime(config, repo_out)           # post-stage-0 merge below won't fire -> re-merge here
                                                   # (sets coverage='none' for docker so stage7 skips the
                                                   # go-mutation path; pulls service/deps for stage5/grade)

    for stage in STAGES:
        if stage < frm or stage > to:
            continue
        if status.get(str(stage)) == "pass":
            print(f"[{repo_id}] stage{stage}: skip (already passed)")
            continue
        print(f"[{repo_id}] stage{stage}: running ...")
        try:
            ok, err = run_stage(stage, repo_id, repo_src, config, repo_out, agent_mode)
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {e}"
        if ok:
            g_ok, g_msg = check_gate(stage, repo_out, config)
            ok, err = g_ok, g_msg
        if not ok:
            status[str(stage)] = f"fail: {err}"
            save_status(repo_out, status)
            tag = " [HUMAN REVIEW]" if stage in HUMAN_GATES else ""
            print(f"[{repo_id}] stage{stage}: FAIL -> {err}{tag}")
            return False
        status[str(stage)] = "pass"
        save_status(repo_out, status)
        if stage == 0:
            _merge_runtime(config, repo_out)   # pull agent-discovered service/pipeline/deps
        print(f"[{repo_id}] stage{stage}: pass")
    print(f"[{repo_id}] DONE (stages {frm}..{to})")
    return True


def run_repo(repo_id, agent_mode="stub", frm=0, to=7, manifest=None):
    if manifest:
        config = cfgmod.load_repo(repo_id, manifest, ROOT)
    else:
        config = json.loads((ROOT / "configs" / f"{repo_id}.json").read_text(encoding="utf-8"))
        config.setdefault("repo_id", repo_id)
        config.setdefault("out_dir", str(ROOT / "out" / repo_id))
    return run_repo_config(config, agent_mode, frm, to)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--manifest", default=None, help="dataset manifest; default configs/<repo>.json")
    ap.add_argument("--agent", choices=["stub", "claude", "codex"], default="stub")
    ap.add_argument("--from", dest="frm", type=int, default=0)
    ap.add_argument("--to", type=int, default=7)
    args = ap.parse_args()
    ok = run_repo(args.repo, args.agent, args.frm, args.to, args.manifest)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
