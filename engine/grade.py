"""Grade a binary against a frozen test suite (dual use: Stage-7 mutation + candidate scoring).

Replays each testcase's input through the target binary and checks the candidate's
observation against the frozen golden assertions. Returns per-test pass/fail with
module tags, so per-module pass-rates can be computed.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
from runner import LocalRunner
import classify
import harness
import replay as replay_mod


def _grade(runner, prefix, backend, config, tests_dir) -> list[dict]:
    results = []
    for tf in sorted(pathlib.Path(tests_dir).glob("*.json")):
        tc = json.loads(tf.read_text(encoding="utf-8"))
        obs = backend.run(runner, prefix, tc["input"], config)
        checks = classify.check(obs, tc["assertions"])
        results.append({"id": tc["id"], "modules": tc.get("modules", []),
                        "ok": all(c["ok"] for c in checks),
                        "fails": [c["field"] for c in checks if not c["ok"]]})
    backend.teardown()   # service: stop deps/SUT ; cli/pipeline: no-op
    return results


def grade_binary(launch: list[str], tests_dir) -> list[dict]:
    """cli/local grading by a bare binary (used by Stage-7 mutation)."""
    runner = LocalRunner(launch[0])
    return _grade(runner, launch[1:], replay_mod.get_backend("cli"), None, tests_dir)


def grade_suite(config: dict, tests_dir) -> list[dict]:
    """Scenario/runtime-agnostic grading via the harness (high-water + candidate scoring).

    For a `go build -cover` SUT, set a throwaway GOCOVERDIR so it does NOT emit the
    "GOCOVERDIR not set, no coverage data emitted" stderr warning — golden was captured
    with GOCOVERDIR set (clean stderr), so grading must match (else every exact-stderr
    assertion fails)."""
    import tempfile
    cover_root = tempfile.mkdtemp(prefix="codebench_grade_") if config.get("coverage") == "go" else None
    runner = harness.make_runner(config, cover_root=cover_root)
    prefix = harness.launch_prefix(config)
    backend = replay_mod.get_backend(config["scenario_type"])
    return _grade(runner, prefix, backend, config, tests_dir)


def score(results: list[dict], modules: list[str]) -> dict:
    """Per-module normalised pass-rate, then cross-module mean (the scheme's functional score)."""
    by_mod = {m: [0, 0] for m in modules}          # [passed, total]
    for r in results:
        for m in r["modules"]:
            if m in by_mod:
                by_mod[m][1] += 1
                by_mod[m][0] += 1 if r["ok"] else 0
    per_module = {m: (p / t if t else None) for m, (p, t) in by_mod.items()}
    rated = [v for v in per_module.values() if v is not None]
    return {"per_module_passrate": per_module,
            "functional": sum(rated) / len(rated) if rated else 0.0,
            "passed": sum(1 for r in results if r["ok"]), "total": len(results)}
