"""Stage 5 - differential-oracle loop with fill_quota + >=20/module enforcement.

Scenario/runtime-agnostic: picks the runner (Local/Docker) and backend (cli/service/
pipeline) via engine/harness. draft_provider(modules, quota, hints) -> (drafts,
needs_review): stub (engine/cli_gen) for offline dev, or the agent (agent/agent_stages).

A draft's input shape is scenario-specific (cli: argv/stdin/files; service: steps;
pipeline: files); the loop treats it opaquely. One test may carry several module tags
(merge-on-collision) so each tag counts toward its module's quota.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import classify
import coverage
import harness
import replay as replay_mod


def _sig(prefix, inp):
    return hashlib.sha1((repr(prefix) + json.dumps(inp, sort_keys=True, default=str)).encode()).hexdigest()


def _preview(obs):
    if obs.extra.get("http"):
        return {"http_status": [s["status"] for s in obs.extra["http"]]}
    if obs.out_files:
        return {"out_files": sorted(obs.out_files.keys())}
    return {"exit": obs.exit_code,
            "stdout_preview": obs.stdout[:120].decode("utf-8", "replace"),
            "stderr_preview": obs.stderr[:120].decode("utf-8", "replace")}


def _testcase(dr, obs, golden):
    tc = {"id": dr["id"], "modules": dr["modules"],
          "scenario_type": dr.get("scenario_type", "cli"), "kind": dr.get("kind", "incident"),
          "note": dr.get("note", ""), "input": dr["input"],
          "observed": _preview(obs), "assertions": golden}
    if dr.get("security_metric"):            # req 2.7: tag which NFR security metric this case evidences
        tc["security_metric"] = dr["security_metric"]
    if dr.get("smoke"):                      # req 2.8: part of the must-pass smoke suite
        tc["smoke"] = True
    return tc


def _smoke_invocations(repo_out, config):
    """Scenario-appropriate smoke INPUTS for the must-pass liveness suite (req 2.8, EACH project):
    - cli      -> the configured 00_runtime `smoke` argv + universal --help/--version/-h probes
    - service  -> one GET on the health endpoint
    - pipeline -> a trivial empty-input run
    Each item is a backend-ready input dict (cli: {argv}; service: {steps}; pipeline: {files})."""
    scen = config.get("scenario_type", "cli")
    if scen == "cli":
        argvs, cfg_smoke = [], config.get("smoke")
        rtj = repo_out / "00_runtime.json"
        if not cfg_smoke and rtj.exists():
            try:
                cfg_smoke = json.loads(rtj.read_text(encoding="utf-8")).get("smoke")
            except Exception:
                cfg_smoke = None
        if isinstance(cfg_smoke, list) and cfg_smoke and all(isinstance(x, str) for x in cfg_smoke):
            argvs.append(list(cfg_smoke))
        for u in (["--help"], ["--version"], ["-h"]):
            if u not in argvs:
                argvs.append(u)
        return [{"argv": a} for a in argvs]
    if scen == "service":
        health = (config.get("service") or {}).get("health", "/health")
        return [{"steps": [{"method": "GET", "path": health}]}]
    if scen == "pipeline":
        return [{"files": {}}]
    return []


def _smoke_spec(obs):
    """A FAIR liveness golden for one smoke observation. Cross-implementation safe: never pins a
    banner's exact exit (a correct reimpl uses different --help/--version exit conventions) — pins
    exit only when the original SUCCEEDED (exit 0), else just output presence.
      - service  -> the health step's status (eq_int; any correct impl returns the same health code)
      - pipeline -> an output file is present (nonempty)
      - cli      -> exit==0 (only if the original succeeded) AND stdout|stderr nonempty (liveness)."""
    http = obs.extra.get("http") if getattr(obs, "extra", None) else None
    if http:
        return [{"field": "http:0:status", "class": "invariant", "rule": f"eq_int:{http[0]['status']}"}]
    if getattr(obs, "out_files", None):
        name = sorted(obs.out_files)[0]
        return [{"field": f"file:{name}", "class": "invariant", "rule": "nonempty"}]
    spec = []
    if obs.exit_code == 0:                       # success liveness is fair; a nonzero banner exit is not
        spec.append({"field": "exit", "class": "invariant", "rule": "eq_int:0"})
    if obs.stdout:
        spec.append({"field": "stdout", "class": "invariant", "rule": "nonempty"})
    elif obs.stderr:
        spec.append({"field": "stderr", "class": "invariant", "rule": "nonempty"})
    return spec


def _smoke_tag(inp, i):
    if inp.get("argv"):
        return "_".join(re.sub(r"[^a-zA-Z0-9]+", "", a) or "x" for a in inp["argv"])[:40] or "x"
    if inp.get("steps"):
        return ("step_" + re.sub(r"[^a-zA-Z0-9]+", "", str(inp["steps"][0].get("path", ""))))[:40] or "step"
    return "run"


def _freeze_smoke(repo_out, config, runner, prefix, backend):
    """Build a packaged, double-run-frozen SMOKE suite (req 2.8) — a fair liveness gate proving a
    candidate build runs and responds. Written to 05_smoke/*.json. Works for cli/service/pipeline."""
    smoke_dir = repo_out / "05_smoke"
    shutil.rmtree(smoke_dir, ignore_errors=True)
    invs = _smoke_invocations(repo_out, config)
    if not invs:
        return 0
    smoke_dir.mkdir(parents=True, exist_ok=True)
    scen, n = config.get("scenario_type", "cli"), 0
    for i, inp in enumerate(invs):
        try:
            obs = backend.run(runner, prefix, inp, config)
        except OSError:
            continue
        if getattr(obs, "timed_out", False) or obs.exit_code == 124:
            continue
        spec = _smoke_spec(obs)
        if not spec:
            continue
        try:
            golden = classify.freeze_golden(obs, spec)
            obs2 = backend.run(runner, prefix, inp, config)        # determinism (double-run, req 2.10)
        except (OSError, AssertionError, ValueError, KeyError):
            continue
        if getattr(obs2, "timed_out", False) or obs2.exit_code == 124:   # flaky on the 2nd run -> drop
            continue
        if not classify.agrees(obs, obs2, golden) or not all(r["ok"] for r in classify.check(obs, golden)):
            continue
        sid = f"smoke_{i}_{_smoke_tag(inp, i)}"
        tc = {"id": sid, "modules": ["SMOKE"], "scenario_type": scen,
              "kind": "smoke", "smoke": True, "note": "liveness smoke (req 2.8)",
              "input": inp, "observed": _preview(obs), "assertions": golden}
        (smoke_dir / f"{sid}.json").write_text(json.dumps(tc, indent=2, ensure_ascii=False), encoding="utf-8")
        n += 1
    return n


def run(repo_out, config, draft_provider, quota: int = 20, max_rounds: int = 3):
    repo_out = pathlib.Path(repo_out)
    lang = config.get("coverage", "none")
    cover_root = str(repo_out / "_cov") if coverage.wants_cover_dirs(lang) else None
    if cover_root:
        shutil.rmtree(cover_root, ignore_errors=True); os.makedirs(cover_root, exist_ok=True)
    tests_dir = repo_out / "05_tests"
    shutil.rmtree(tests_dir, ignore_errors=True); tests_dir.mkdir(parents=True, exist_ok=True)

    runner = harness.make_runner(config, cover_root)
    prefix = harness.launch_prefix(config)
    backend = replay_mod.get_backend(config["scenario_type"], config)   # config -> local vs docker service
    modules = [m["id"] for m in json.loads(
        (repo_out / "03_modules.json").read_text(encoding="utf-8"))["modules"]]
    # program/binary name (req 6): drafts must NOT pass it as argv[0] (that turns the program name into
    # a bogus positional argument). Captured from the contract so the loop can drop such invocations.
    prog_name = ""
    _cp = repo_out / "02_cli-contract.json"
    if _cp.exists():
        try:
            prog_name = str(json.loads(_cp.read_text(encoding="utf-8")).get("binary", "")).strip()
        except Exception:
            prog_name = ""

    seen, emitted_by_sig, cover_dirs, emitted, climb = set(), {}, [], [], []
    per_module = {m: 0 for m in modules}
    needs_review, untagged, hints, dropped, dropped_nondet, dropped_run_error, dropped_timeout = \
        set(), 0, [], 0, 0, 0, 0
    dropped_argv_binary = 0

    for rnd in range(max_rounds):
        target = modules if rnd == 0 else [m for m in modules
                                           if per_module[m] < quota and m not in needs_review]
        drafts, nr = draft_provider(target, quota, hints)
        needs_review |= set(nr)
        new_this_round = 0
        for dr in drafts:
            if not dr.get("modules"):
                untagged += 1
                continue
            inp = dr["input"]
            argv0 = (inp.get("argv") or [None])[0]
            if prog_name and isinstance(argv0, str) and argv0.strip() == prog_name:
                dropped_argv_binary += 1   # program name wrongly passed as argv[0] -> bogus invocation (req 6)
                continue
            sig = _sig(prefix, inp)
            if sig in seen:
                tc, path = emitted_by_sig[sig]
                changed = False
                for m in dr["modules"]:
                    if m not in tc["modules"]:
                        tc["modules"].append(m)
                        if m in per_module:
                            per_module[m] += 1
                        changed = True
                if changed:
                    path.write_text(json.dumps(tc, indent=2, ensure_ascii=False), encoding="utf-8")
                continue
            try:
                obs = backend.run(runner, prefix, inp, config)        # run 1 (network allowed)
                golden = classify.freeze_golden(obs, dr.get("assert_spec"))
            except (AssertionError, ValueError, KeyError):
                dropped += 1          # malformed assertion (bad rule/field) or invariant fails on ref -> drop
                continue
            except OSError:
                dropped_run_error += 1  # backend/runtime failure on this input -> drop, don't crash the repo
                continue
            if getattr(obs, "timed_out", False) or obs.exit_code == 124:
                dropped_timeout += 1   # timeout/124 = environment artifact (network hang), not contract -> drop
                continue
            try:
                obs2 = backend.run(runner, prefix, inp, config)       # run 2: determinism check
            except OSError:
                dropped_run_error += 1
                continue
            if not classify.agrees(obs, obs2, golden):
                dropped_nondet += 1   # two runs differ -> non-deterministic input -> drop
                continue
            if not all(r["ok"] for r in classify.check(obs, golden)):
                continue
            seen.add(sig)
            tc = _testcase(dr, obs, golden)
            path = tests_dir / f"{dr['id']}.json"
            path.write_text(json.dumps(tc, indent=2, ensure_ascii=False), encoding="utf-8")
            emitted_by_sig[sig] = (tc, path)
            emitted.append(tc)
            new_this_round += 1
            if obs.cover_dir:
                cover_dirs.append(obs.cover_dir)
            for m in dr["modules"]:
                if m in per_module:
                    per_module[m] += 1

        if coverage.wants_cover_dirs(lang) and cover_dirs:
            climb.append([len(emitted), coverage.pct(lang, cover_dirs)])
            hints = coverage.collect(lang, cover_dirs, str(repo_out / "05_coverage.profile"))["uncovered"]
        under = [m for m in modules if per_module[m] < quota and m not in needs_review]
        if not under:
            break
        if new_this_round == 0:
            needs_review |= set(under)
            break

    # any module still short after all rounds is exhausted within budget -> flag for human review
    needs_review |= {m for m in modules if per_module[m] < quota}
    smoke_n = _freeze_smoke(repo_out, config, runner, prefix, backend)   # req 2.8 (before teardown)
    backend.teardown()   # service: flush SUT coverage + stop deps/SUT ; cli/pipeline: no-op
    led = (coverage.collect(lang, cover_dirs, str(repo_out / "05_coverage.profile"))
           if cover_dirs else {"uncovered": [], "pct_statements": 0.0, "block_coverage": 0.0})
    sec_by_metric = {}
    for t in emitted:
        if t.get("security_metric"):
            sec_by_metric[t["security_metric"]] = sec_by_metric.get(t["security_metric"], 0) + 1
    summary = {"repo_id": config["repo_id"], "scenario_type": config["scenario_type"],
               "tests_emitted": len(emitted), "per_module": per_module,
               "security_tests": sum(sec_by_metric.values()), "security_by_metric": sec_by_metric,
               "smoke_tests": smoke_n,
               "needs_review": sorted(needs_review), "untagged_tests": untagged,
               "dropped_bad_spec": dropped, "dropped_nondeterministic": dropped_nondet,
               "dropped_run_error": dropped_run_error, "dropped_timeout": dropped_timeout,
               "dropped_argv_binary": dropped_argv_binary, "quota": quota,
               "intent": sum(1 for t in emitted if t["kind"] == "intent"),
               "incident": sum(1 for t in emitted if t["kind"] == "incident"),
               "pct_statements": led.get("pct_statements", 0.0),
               "uncovered_blocks": len(led.get("uncovered", [])), "coverage_climb": climb}
    (repo_out / "05_coverage-ledger.json").write_text(
        json.dumps({"summary": summary, "uncovered_sample": led.get("uncovered", [])[:12]},
                   indent=2), encoding="utf-8")
    return summary
