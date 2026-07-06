"""Generic CLI differential-oracle loop (config-driven; not tied to any one repo).

Run via run_repo.py with a config dict:
  {
    "repo_id": "gron",
    "launch":  ["D:/code-bench/bin/gron_cov.exe"],   # or ["python","-m","tool"], any launcher
    "drafts":  "path/to/drafts.json",                # the input matrix (no expected values)
    "out_dir": "D:/code-bench/out/gron",
    "coverage":"go" | "none"                          # "go" needs a `go build -cover` binary
  }

A draft (one per testcase) - model-authored input, NO expected values:
  { "id": "...", "modules": ["M1"], "kind": "intent|incident",
    "input": { "argv": ["-m"], "stdin": "<utf8>"  | "stdin_b64": "<b64>",
               "files": {"in.json": {"text": "..."} | {"b64": "..."} } },
    "assert_spec": [ {"field":"exit","class":"exact"},
                     {"field":"stdout","class":"normalized","rule":"crlf_lf"} ] }

The original's real outputs become the golden (freeze_golden). Emits out_dir/05_tests/*
and out_dir/05_coverage-ledger.json.
"""
import base64
import hashlib
import json
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from runner import LocalRunner, Invocation
import classify
import gocover

SUCCESS = [{"field": "exit", "class": "exact"},
           {"field": "stdout", "class": "normalized", "rule": "crlf_lf"}]


def _stdin_bytes(inp):
    if "stdin_b64" in inp:
        return base64.b64decode(inp["stdin_b64"])
    if "stdin" in inp and inp["stdin"] is not None:
        return inp["stdin"].encode("utf-8")
    return b""


def _file_bytes(v):
    if isinstance(v, str):                       # back-compat: bare string = base64
        return base64.b64decode(v)
    if "b64" in v:
        return base64.b64decode(v["b64"])
    return v.get("text", "").encode("utf-8")


def run(config):
    out = pathlib.Path(config["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    cov_mode = config.get("coverage", "none")
    cover_root = str(out / "_cov") if cov_mode == "go" else None
    if cover_root:
        shutil.rmtree(cover_root, ignore_errors=True)
        os.makedirs(cover_root, exist_ok=True)
    tests_dir = out / "05_tests"
    shutil.rmtree(tests_dir, ignore_errors=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    launch = config.get("launch") or [config["binary"]]
    runner = LocalRunner(launch[0], cover_root=cover_root)
    prefix = launch[1:]

    drafts = json.loads(pathlib.Path(config["drafts"]).read_text(encoding="utf-8"))

    seen, per_module, cover_dirs, emitted, checkpoints = set(), {}, [], [], []
    kept = 0
    for dr in drafts:
        inp = dr["input"]
        stdin = _stdin_bytes(inp)
        files = {k: _file_bytes(v) for k, v in inp.get("files", {}).items()}
        inv = Invocation(argv=prefix + inp.get("argv", []), stdin=stdin, files=files)
        obs = runner.run(inv)

        sig = hashlib.sha1((repr(inv.argv) + base64.b64encode(stdin).decode() +
                            repr(sorted(files.keys()))).encode()).hexdigest()
        if sig in seen:
            continue
        seen.add(sig)

        spec = dr.get("assert_spec", SUCCESS)
        try:
            golden = classify.freeze_golden(obs, spec)
        except AssertionError as e:
            print(f"  ! {dr['id']}: bad assertion -> {e}")
            continue
        if not all(r["ok"] for r in classify.check(obs, golden)):
            print(f"  ! {dr['id']}: self-check failed (engine bug?)")
            continue

        tc = {"id": dr["id"], "modules": dr.get("modules", []), "scenario_type": "cli",
              "kind": dr.get("kind", "incident"), "note": dr.get("note", ""),
              "input": {"argv": inp.get("argv", []),
                        "stdin_b64": base64.b64encode(stdin).decode(),
                        "files": {k: base64.b64encode(v).decode() for k, v in files.items()}},
              "observed": {"exit": obs.exit_code,
                           "stdout_preview": obs.stdout[:120].decode("utf-8", "replace"),
                           "stderr_preview": obs.stderr[:120].decode("utf-8", "replace")},
              "assertions": golden}
        (tests_dir / f"{dr['id']}.json").write_text(
            json.dumps(tc, indent=2, ensure_ascii=False), encoding="utf-8")
        emitted.append(tc)
        if obs.cover_dir:
            cover_dirs.append(obs.cover_dir)
        kept += 1
        for m in dr.get("modules", []):
            per_module[m] = per_module.get(m, 0) + 1
        if cov_mode == "go" and kept in (1, 5, 10, 20, 30, len(drafts)):
            checkpoints.append((kept, gocover.pct_value(cover_dirs)))

    summary = {"repo_id": config["repo_id"], "tests_emitted": kept, "per_module": per_module,
               "intent": sum(1 for t in emitted if t["kind"] == "intent"),
               "incident": sum(1 for t in emitted if t["kind"] == "incident")}
    if cov_mode == "go" and cover_dirs:
        led = gocover.ledger(cover_dirs, str(out / "05_coverage.profile"))
        summary.update({"pct_statements": led["pct_statements"],
                        "uncovered_blocks": len(led["uncovered"]),
                        "coverage_climb": checkpoints})
        uncovered_sample = led["uncovered"][:12]
    else:
        summary["coverage"] = "none (no instrumented binary) - testcases still valid, no coverage signal"
        uncovered_sample = []

    (out / "05_coverage-ledger.json").write_text(
        json.dumps({"summary": summary, "uncovered_sample": uncovered_sample}, indent=2),
        encoding="utf-8")

    print(f"=== {config['repo_id']}: emitted {kept} testcases "
          f"(intent={summary['intent']} incident={summary['incident']}) ===")
    print("per-module:", json.dumps(per_module))
    if cov_mode == "go" and cover_dirs:
        print("coverage climb:", checkpoints, "-> final", summary["pct_statements"], "% ,",
              summary["uncovered_blocks"], "uncovered blocks")
    print("written to", tests_dir)
    return summary
