"""Stage 5 - differential-oracle test-generation loop (gron pilot, cli backend).

Flow per draft (what a model would emit: input + assertion CLASSES, no values):
  1. build an Invocation (argv + exact stdin bytes + input files)
  2. run it through the ORIGINAL's `-cover` binary  -> Observation + per-run coverage
  3. freeze_golden(): the original's outputs BECOME the golden (differential oracle)
  4. self-check the frozen assertions against that same Observation (sanity)
  5. dedup by behavioural signature, tag to modules, accumulate coverage

Emits: 05_input-drafts.json, 05_tests/<id>.json, 05_coverage-ledger.json
In production the draft matrix is model-generated and looped (fill_quota) to >=20
per module using the uncovered-block hints; here it is a fixed representative set.
"""
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

REPO = pathlib.Path(r"D:\code-bench\repos\gron")
BIN = r"D:\code-bench\bin\gron_cov.exe"
OUT = pathlib.Path(r"D:\code-bench\out\gron")
COVROOT = OUT / "_cov_loop"
TESTS = OUT / "05_tests"

SUCCESS = [{"field": "exit", "class": "exact"},
           {"field": "stdout", "class": "normalized", "rule": "crlf_lf"}]
ERROR = [{"field": "exit", "class": "exact"},
         {"field": "stderr", "class": "invariant", "rule": "nonempty"},
         {"field": "stderr", "class": "ignored"}]


def td(name):
    return (REPO / "testdata" / name).read_bytes()


def D(id, modules, argv, stdin=b"", files=None, spec=None, kind="incident", note=""):
    if isinstance(stdin, str):
        stdin = stdin.encode("utf-8")
    return {"id": id, "modules": modules, "scenario_type": "cli", "kind": kind,
            "note": note, "input": {"argv": argv, "stdin_b64": _b64(stdin),
                                    "files": {k: _b64(v) for k, v in (files or {}).items()}},
            "assert_spec": spec or SUCCESS}


def _b64(b):
    import base64
    return base64.b64encode(b).decode("ascii")


def _unb64(s):
    import base64
    return base64.b64decode(s.encode("ascii"))


def draft_matrix():
    d = []
    # ---- M1 encode (JSON -> sorted statements) ----
    for n in ["one.json", "two.json", "three.json", "github.json"]:
        d.append(D(f"M1-enc-{n.split('.')[0]}", ["M1"], ["-m"], td(n), kind="intent",
                   note=f"repo testdata {n} (intent golden)"))
    d += [
        D("M1-scalar-num", ["M1"], ["-m"], "42"),
        D("M1-scalar-str", ["M1"], ["-m"], '"hi"'),
        D("M1-bool", ["M1"], ["-m"], "true"),
        D("M1-null", ["M1"], ["-m"], "null"),
        D("M1-empty-obj", ["M1"], ["-m"], "{}"),
        D("M1-empty-arr", ["M1"], ["-m"], "[]"),
        D("M1-nested", ["M1"], ["-m"], '{"a":{"b":[1,2]}}'),
        # utf-8 value -> exact byte assertion to prove byte fidelity
        D("M1-unicode", ["M1"], ["-m"], '{"k":"café"}',
          spec=[{"field": "exit", "class": "exact"}, {"field": "stdout", "class": "exact"}]),
        D("M1-space-key", ["M1"], ["-m"], '{"a b":1}',
          note="key needs bracket notation"),
    ]
    # ---- M2 ungron (statements -> JSON) ----
    for n in ["one", "two", "three", "github", "grep-separators"]:
        d.append(D(f"M2-dec-{n}", ["M2"], ["-m", "-u"], td(f"{n}.gron"), kind="intent",
                   spec=[{"field": "exit", "class": "exact"},
                         {"field": "stdout", "class": "invariant", "rule": "valid_json"},
                         {"field": "stdout", "class": "normalized", "rule": "json_canonical"}],
                   note=f"repo testdata {n}.gron (intent)"))
    # ---- M3 values (-v) ----
    d += [
        D("M3-values-basic", ["M3"], ["-m", "-v"],
          'json.name = "Sam";\njson.age = 30;\n'),
        D("M3-values-bool-null", ["M3"], ["-m", "-v"],
          'json.ok = true;\njson.x = null;\n'),
        D("M3-values-nested", ["M3"], ["-m", "-v"],
          'json.a.b = "deep";\njson.a.c = 7;\n'),
    ]
    # ---- M4 stream (-s) ----
    d += [
        D("M4-stream", ["M4"], ["-m", "-s"], td("stream.json"), kind="intent"),
        D("M4-scalar-stream", ["M4"], ["-m", "-s"], td("scalar-stream.json"), kind="intent"),
        D("M4-stream-inline", ["M4"], ["-m", "-s"], '{"a":1}\n{"b":2}\n'),
    ]
    # ---- M5 json representation (-j) ----
    for n in ["one", "two", "github"]:
        d.append(D(f"M5-jgron-{n}", ["M5"], ["-m", "-j"], td(f"{n}.json"), kind="intent"))
    d.append(D("M5-ungron-j", ["M5", "M2"], ["-m", "-u", "-j"], td("one.jgron"), kind="intent",
               spec=[{"field": "exit", "class": "exact"},
                     {"field": "stdout", "class": "invariant", "rule": "valid_json"}]))
    # ---- M6 output control ----
    d += [
        D("M6-nosort-array", ["M6"], ["-m", "--no-sort"], "[3,1,2]",
          note="array order is deterministic"),
        D("M6-nosort-object", ["M6"], ["-m", "--no-sort"], '{"b":1,"a":2}',
          spec=[{"field": "exit", "class": "exact"},
                {"field": "stdout", "class": "normalized", "rule": "lines_sorted"}],
          note="object iteration order is NONDETERMINISTIC -> normalize as a set of lines"),
        D("M6-colorize", ["M6"], ["-c"], '{"a":1}',
          spec=[{"field": "exit", "class": "exact"},
                {"field": "stdout", "class": "invariant", "rule": "regex:\\x1b\\["}],
          note="-c forces ANSI even on a pipe -> non-portable, assert 'contains ANSI' only"),
        D("M6-monochrome", ["M6"], ["-m"], '{"a":1}'),
    ]
    # ---- M7 input source ----
    d += [
        D("M7-file-arg", ["M7"], ["-m", "in.json"], files={"in.json": td("two.json")},
          note="input from a file argument placed in the workdir"),
        D("M7-dash-stdin", ["M7"], ["-m", "-"], td("one.json"),
          note="'-' means stdin"),
        D("M7-empty-stdin", ["M7"], ["-m"], b"", spec=ERROR,
          note="empty input -> JSON decode error"),
    ]
    # ---- M8 cli meta / errors (golden = whatever the original returns) ----
    d += [
        D("M8-version", ["M8"], ["--version"],
          spec=[{"field": "exit", "class": "exact"},
                {"field": "stdout", "class": "invariant", "rule": "regex:gron version"}]),
        D("M8-help", ["M8"], ["-h"], spec=[{"field": "exit", "class": "exact"},
                                           {"field": "stderr", "class": "invariant", "rule": "regex:Usage"},
                                           {"field": "stderr", "class": "ignored"}]),
        D("M8-bad-json", ["M8"], ["-m"], "{bad", spec=ERROR),
        D("M8-ungron-garbage", ["M8", "M2"], ["-m", "-u"], "this is not gron @@@", spec=ERROR),
        D("M8-missing-file", ["M8", "M7"], ["-m", "nope.json"], spec=ERROR),
    ]
    return d


def run():
    shutil.rmtree(COVROOT, ignore_errors=True); os.makedirs(COVROOT, exist_ok=True)
    shutil.rmtree(TESTS, ignore_errors=True); os.makedirs(TESTS, exist_ok=True)
    runner = LocalRunner(BIN, cover_root=str(COVROOT))

    drafts = draft_matrix()
    (OUT / "05_input-drafts.json").write_text(json.dumps(drafts, indent=2), encoding="utf-8")

    seen = set()
    per_module = {}
    cover_dirs = []
    emitted = []
    checkpoints = []
    kept = 0

    for i, dr in enumerate(drafts):
        inp = dr["input"]
        inv = Invocation(argv=inp["argv"], stdin=_unb64(inp["stdin_b64"]),
                         files={k: _unb64(v) for k, v in inp["files"].items()})
        obs = runner.run(inv)

        # dedup by behavioural signature (argv + stdin + files), not by code line
        sig = hashlib.sha1((repr(inp["argv"]) + inp["stdin_b64"] +
                            repr(sorted(inp["files"].items()))).encode()).hexdigest()
        if sig in seen:
            continue
        seen.add(sig)

        # differential oracle: the original's outputs become the golden
        try:
            golden = classify.freeze_golden(obs, dr["assert_spec"])
        except AssertionError as e:
            print(f"  ! {dr['id']}: bad assertion choice -> {e}")
            continue
        selfcheck = classify.check(obs, golden)
        if not all(r["ok"] for r in selfcheck):
            print(f"  ! {dr['id']}: self-check failed (should never happen): {selfcheck}")
            continue

        testcase = {"id": dr["id"], "modules": dr["modules"], "scenario_type": "cli",
                    "kind": dr["kind"], "note": dr["note"], "input": inp,
                    "observed": {"exit": obs.exit_code,
                                 "stdout_preview": obs.stdout[:120].decode("utf-8", "replace"),
                                 "stderr_preview": obs.stderr[:120].decode("utf-8", "replace")},
                    "assertions": golden}
        (TESTS / f"{dr['id']}.json").write_text(json.dumps(testcase, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
        emitted.append(testcase)
        cover_dirs.append(obs.cover_dir)
        kept += 1
        for m in dr["modules"]:
            per_module[m] = per_module.get(m, 0) + 1

        # record the coverage climb at a few checkpoints
        if kept in (1, 5, 10, 20, 30, len(drafts)):
            checkpoints.append((kept, gocover.pct_value(cover_dirs)))

    led = gocover.ledger(cover_dirs, str(OUT / "05_coverage.profile"))
    summary = {"tests_emitted": kept, "per_module": per_module,
               "intent": sum(1 for t in emitted if t["kind"] == "intent"),
               "incident": sum(1 for t in emitted if t["kind"] == "incident"),
               "pct_statements": led["pct_statements"],
               "block_coverage": round(led["block_coverage"], 3),
               "uncovered_blocks": len(led["uncovered"]),
               "coverage_climb": checkpoints}
    (OUT / "05_coverage-ledger.json").write_text(
        json.dumps({"summary": summary, "uncovered_sample": led["uncovered"][:12]},
                   indent=2), encoding="utf-8")

    print("=== Stage 5 loop: gron ===")
    print(f"drafts={len(drafts)}  emitted={kept}  (intent={summary['intent']} incident={summary['incident']})")
    print("per-module test counts:", json.dumps(per_module))
    print("coverage climb (n_tests -> %stmt):", checkpoints)
    print(f"final: {led['pct_statements']}% statements, {summary['uncovered_blocks']} uncovered blocks")
    print("uncovered sample (behaviour-discovery hints for next round):")
    for u in led["uncovered"][:6]:
        print("   ", u)
    print("\nsample testcase (M1-unicode, exact byte assertion):")
    print((TESTS / "M1-unicode.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
