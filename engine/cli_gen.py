"""Equivalence-class draft generator for the cli scenario (gron-shaped STUB).

In the real pipeline the input drafts are produced by the out-题 agent (Stage 5
"model writes inputs"), guided by uncovered-block hints. Here, with no live agent
in the loop, this module stands in: per module it crosses a *mode* (argv + how to
feed input + assertion classes) with a *corpus* of distinct payloads (equivalence
classes), dedups, and yields up to `quota` drafts. If a module's distinct space is
smaller than the quota it is returned in `needs_review` (quality gate > quota) -
never padded with filler.

This is intentionally gron-aware; swap it for the agent by setting --agent claude.
"""
from __future__ import annotations

import hashlib

SUCCESS = [{"field": "exit", "class": "exact"},
           {"field": "stdout", "class": "normalized", "rule": "crlf_lf"}]
JSONOUT = [{"field": "exit", "class": "exact"},
           {"field": "stdout", "class": "invariant", "rule": "valid_json"},
           {"field": "stdout", "class": "normalized", "rule": "json_canonical"}]
META = [{"field": "exit", "class": "exact"},
        {"field": "stderr", "class": "ignored"}]

# distinct JSON inputs (equivalence classes: scalars, containers, nesting, unicode, escapes, edge keys)
JSON_CORPUS = [
    "5", "-0", "0", "3.14", "1e10",
    '"hi"', '""', '"a\\"b"', "true", "false", "null",
    "{}", "[]", "[1,2,3]", '{"a":1}', '{"b":2,"a":1}', '{"z":3,"a":1,"m":2}',
    '{"a":{"b":{"c":1}}}', '{"k":"café"}', '{"one":1,"two":2,"three":3}',
    '{"a b":1}', '{"":1}', '[null,true,1,"x"]', '{"n":1.5,"s":"y","b":false}',
    '[[1],[2,[3]]]', '{"u":"日本語"}', '[{"id":1},{"id":2}]', "123456789012345",
]
# distinct gron-statement inputs for ungron / values
GRON_CORPUS = [
    "json = 1;", 'json = "x";', "json = true;", "json = null;", "json = [];", "json = {};",
    "json.a = 1;", 'json.a = "x";', "json.a.b = 2;", "json[0] = 1;\njson[1] = 2;",
    "json.list = [];\njson.list[0] = 1;", 'json.nested.deep.key = "v";',
    "json.a = 1;\njson.b = 2;\njson.c = 3;", 'json["a b"] = 1;', "json.num = 3.14;",
    "json.neg = -5;", "json.t = true;\njson.f = false;", 'json.unicode = "café";',
    'json.empty = "";', "json.obj = {};\njson.obj.k = 1;",
    'json.mix = [];\njson.mix[0] = 1;\njson.mix[1] = "two";', "json.big = 123456789012345;",
]
OBJ_LINES = ['{"a":1}', '{"b":2}', '{"c":[1,2]}', '{"n":null}', '{"s":"x"}',
             '{"t":true}', "5", '"str"', "[1,2]", "{}", '{"d":3}', '{"e":4}']
# distinct error/meta inputs for cli-meta
ERROR_INPUTS = [
    "{bad", "[1,", '{"a":}', "tru", "{,}", "[}", '"unterminated', '{"a":1,}',
    "nul", "12.3.4", "}{", "[1 2]", "   ", "@@@", "{[]}", '{"a" 1}',
]


def _sig(argv, stdin, files):
    return hashlib.sha1((repr(argv) + repr(stdin) + repr(sorted((files or {}).keys()))).encode()).hexdigest()


def _draft(id, m, argv, spec, stdin=None, files=None, note=""):
    inp = {"argv": argv}
    if stdin is not None:
        inp["stdin"] = stdin
    if files:
        inp["files"] = files
    return {"id": id, "modules": [m], "scenario_type": "cli", "kind": "incident",
            "note": note, "input": inp, "assert_spec": spec}


def _m6_spec(argv, payload):
    if "-c" in argv:
        return [{"field": "exit", "class": "exact"},
                {"field": "stdout", "class": "invariant", "rule": "regex:\\x1b\\["}]
    if "--no-sort" in argv and payload.strip().startswith("{"):
        return [{"field": "exit", "class": "exact"},
                {"field": "stdout", "class": "normalized", "rule": "lines_sorted"}]
    return SUCCESS


def module_drafts(m: str, quota: int):
    """Yield up to `quota` distinct drafts for module m."""
    out, seen = [], set()

    def add(d):
        s = _sig(d["input"]["argv"], d["input"].get("stdin"), d["input"].get("files"))
        if s in seen:
            return
        seen.add(s)
        out.append(d)

    if m == "M1":
        for i, p in enumerate(JSON_CORPUS):
            add(_draft(f"M1-{i:02d}", m, ["-m"], SUCCESS, stdin=p))
    elif m == "M2":
        for i, p in enumerate(GRON_CORPUS):
            add(_draft(f"M2-{i:02d}", m, ["-m", "-u"], JSONOUT, stdin=p))
    elif m == "M3":
        for i, p in enumerate(GRON_CORPUS):
            add(_draft(f"M3-{i:02d}", m, ["-m", "-v"], SUCCESS, stdin=p))
    elif m == "M4":
        idx = 0
        for k in (2, 3, 4):
            for i in range(len(OBJ_LINES) - k + 1):
                payload = "\n".join(OBJ_LINES[i:i + k]) + "\n"
                add(_draft(f"M4-{idx:02d}", m, ["-m", "-s"], SUCCESS, stdin=payload)); idx += 1
    elif m == "M5":
        for i, p in enumerate(JSON_CORPUS):
            add(_draft(f"M5-{i:02d}", m, ["-m", "-j"], SUCCESS, stdin=p))
    elif m == "M6":
        idx = 0
        for p in JSON_CORPUS:
            for argv in (["-m"], ["-c"], ["--no-sort", "-m"], ["-m", "-j"], ["--no-sort", "-m", "-j"]):
                add(_draft(f"M6-{idx:02d}", m, argv, _m6_spec(argv, p), stdin=p)); idx += 1
    elif m == "M7":
        idx = 0
        for p in JSON_CORPUS:
            add(_draft(f"M7-{idx:02d}a", m, ["-m"], SUCCESS, stdin=p, note="stdin")); idx += 1
            add(_draft(f"M7-{idx:02d}b", m, ["-m", "in.json"], SUCCESS,
                       files={"in.json": {"text": p}}, note="file arg")); idx += 1
            add(_draft(f"M7-{idx:02d}c", m, ["-m", "-"], SUCCESS, stdin=p, note="dash=stdin")); idx += 1
    elif m == "M8":
        add(_draft("M8-version", m, ["--version"],
                   [{"field": "exit", "class": "exact"},
                    {"field": "stdout", "class": "invariant", "rule": "regex:gron version"}]))
        add(_draft("M8-help", m, ["-h"],
                   [{"field": "exit", "class": "exact"},
                    {"field": "stderr", "class": "invariant", "rule": "regex:Usage"},
                    {"field": "stderr", "class": "ignored"}]))
        for i, e in enumerate(ERROR_INPUTS):
            add(_draft(f"M8-err{i:02d}", m, ["-m"], META, stdin=e, note="bad input"))
        for i, fn in enumerate(["nope.json", "missing2.json", "no/such.json"]):
            add(_draft(f"M8-nofile{i}", m, ["-m", fn], META, note="missing file"))
        for i, g in enumerate(["garbage @@@", "= 5;", "json.a"]):
            add(_draft(f"M8-badu{i}", m, ["-m", "-u"], META, stdin=g, note="bad ungron"))
    else:
        return [], True

    needs_review = len(out) < quota
    return out[:quota], needs_review


def generate(modules: list[str], quota: int = 20):
    """Return (drafts, needs_review_modules)."""
    drafts, needs_review = [], []
    for m in modules:
        d, nr = module_drafts(m, quota)
        drafts.extend(d)
        if nr:
            needs_review.append(m)
    return drafts, needs_review
