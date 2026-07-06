#!/usr/bin/env python3
"""Rerun functional grader cases and compute module-level requirement coverage.

This script is intended to run on the benchmark server. It writes new artifacts
under /mnt/yangh559/chuti-run without modifying existing score.json files.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import traceback
from collections import defaultdict

PREFIX = pathlib.Path("/mnt/yangh559")
CODE = PREFIX / "code-bench-v2"
STATE = PREFIX / "chuti-run"
GRADES = STATE / "grades"
SUBS = STATE / "submissions"
OUT = CODE / "out"

FUNC_KEY = "\u529f\u80fd\u5206"
EXCLUDE_REPOS = {"dosisod-refurb"}
DEFAULT_AGENTS = ["claude", "codex", "cursor", "kimi"]


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _text(v):
    return bytes(v).decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else str(v)


def _extract(obs, field):
    if field == "exit":
        return obs["exit"]
    if field == "stdout":
        return obs["stdout"]
    if field == "stderr":
        return obs["stderr"]
    if field.startswith("file:"):
        return obs.get("files", {}).get(field[5:])
    raise KeyError(field)


def _enc(v):
    if isinstance(v, bool):
        return {"bool": v}
    if isinstance(v, int):
        return {"int": v}
    if v is None:
        return {"null": True}
    b = bytes(v) if isinstance(v, (bytes, bytearray)) else str(v).encode()
    try:
        t = b.decode("utf-8")
        if t.encode() == b:
            return {"utf8": t}
    except Exception:
        pass
    return {"b64": base64.b64encode(b).decode()}


def _norm(rule, v):
    t = _text(v)
    if rule == "crlf_lf":
        return t.replace("\r\n", "\n")
    if rule == "strip":
        return t.strip()
    if rule == "rstrip_eol":
        return "\n".join(l.rstrip() for l in t.replace("\r\n", "\n").split("\n")).strip("\n")
    if rule == "lines_sorted":
        return "\n".join(sorted(t.replace("\r\n", "\n").rstrip("\n").split("\n")))
    if rule == "json_canonical":
        return json.dumps(json.loads(t), sort_keys=True, separators=(",", ":"))
    if rule.startswith("regex_extract:"):
        m = re.search(rule[len("regex_extract:"):], t, re.S)
        return m.group(0) if m else None
    raise ValueError("bad normalize rule: " + rule)


def _inv(rule, v):
    t = _text(v)
    if rule == "nonempty":
        return len(t) > 0
    if rule == "empty":
        return len(t) == 0
    if rule == "valid_json":
        try:
            json.loads(t)
            return True
        except Exception:
            return False
    if rule.startswith("regex:"):
        return re.search(rule[len("regex:"):], t, re.S) is not None
    if rule.startswith("eq_int:"):
        try:
            return int(v) == int(rule[len("eq_int:"):])
        except Exception:
            return False
    raise ValueError("bad invariant rule: " + rule)


def check_assertions(obs, assertions):
    fails = []
    for a in assertions:
        f, cls = a["field"], a["class"]
        try:
            val = _extract(obs, f)
            if cls == "exact":
                ok = _enc(val) == a["value"]
                msg = "exact mismatch"
            elif cls == "normalized":
                ok = _norm(a["rule"], val) == a["value"]
                msg = f"normalized({a['rule']}) mismatch"
            elif cls == "invariant":
                ok = _inv(a["rule"], val)
                msg = f"invariant({a['rule']}) failed"
            elif cls == "ignored":
                ok = True
                msg = ""
            else:
                ok = False
                msg = "unknown assertion class"
        except Exception as e:
            ok = False
            msg = f"{type(e).__name__}: {e}"
        if not ok:
            fails.append({"field": f, "class": cls, "message": msg})
    return fails


def file_bytes(v):
    if isinstance(v, str):
        return base64.b64decode(v)
    return base64.b64decode(v["b64"]) if "b64" in v else v.get("text", "").encode("utf-8")


def stdin_bytes(inp):
    if inp.get("stdin_b64"):
        return base64.b64decode(inp["stdin_b64"])
    return (inp.get("stdin") or "").encode("utf-8")


def fixed_launch(work):
    run = load_json(work / "run.json", {}) or {}
    launch = run.get("launch", [])
    if not isinstance(launch, list):
        return []

    def fix(p):
        p = str(p)
        m = re.match(r"^/(?:tmp|root)/exam_work/[^/]+/[^/]+/(.*)$", p)
        if m:
            return str(work / m.group(1))
        if not p.startswith("/") and ("/" in p or (work / p).exists()):
            return str(work / p)
        return p

    return [fix(x) for x in launch]


def _run_build(work):
    build = work / "build.sh"
    build_msg = ""
    if build.exists():
        try:
            p = subprocess.run(["bash", str(build)], cwd=str(work), capture_output=True,
                               text=True, timeout=900)
            if p.returncode != 0:
                build_msg = (p.stdout + p.stderr)[-3000:]
        except Exception as e:
            build_msg = f"build exception: {type(e).__name__}: {e}"
    else:
        build_msg = "missing build.sh"
    return build_msg


def _wrap_launch(work, launch):
    wrap = work / ".candidate_launch_metrics.sh"
    wrap.write_text("#!/usr/bin/env bash\nexec %s \"$@\"\n" % " ".join(launch), encoding="utf-8")
    wrap.chmod(0o755)
    return [str(wrap)]


def prepare_candidate(work, build_mode="missing", use_wrapper=False):
    """Prepare a launch command.

    build_mode=missing reproduces the main metrics run: use existing artifacts and
    rebuild only when launch[0] is an absolute path that no longer exists.
    build_mode=always mirrors grade_worker.sh more closely, but can perturb old
    submissions whose build.sh re-downloads toolchains.
    """
    build_msg = ""
    launch = fixed_launch(work)

    if build_mode == "always":
        build_msg = _run_build(work)
        launch = fixed_launch(work)
    elif build_mode == "missing":
        first = launch[0] if launch else ""
        if (not launch) or (first.startswith("/") and not pathlib.Path(first).exists()):
            build_msg = _run_build(work)
            launch = fixed_launch(work)
    else:
        return False, f"unknown build_mode: {build_mode}", []

    launch = fixed_launch(work)
    if not launch:
        return False, build_msg or "missing launch", []
    return True, build_msg, _wrap_launch(work, launch) if use_wrapper else launch


def run_one_case(case, launch, timeout):
    inp = case.get("input", {})
    argv = inp.get("argv", [])
    files = {k: file_bytes(v) for k, v in inp.get("files", {}).items()}
    work = tempfile.mkdtemp(prefix="codebench_metric_case_")
    try:
        before = {}
        for name, data in files.items():
            p = pathlib.Path(work, name)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            before[name] = data
        env = dict(os.environ, TZ="UTC", LC_ALL="C", NO_COLOR="1")
        t0 = time.monotonic()
        timed_out = False
        crashed = False
        try:
            p = subprocess.run([*launch, *argv], input=stdin_bytes(inp), capture_output=True,
                               cwd=work, env=env, timeout=timeout)
            rc = p.returncode
            stdout = p.stdout
            stderr = p.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            rc = 124
            stdout = e.stdout or b""
            stderr = e.stderr or b""
        except Exception as e:
            crashed = True
            rc = 127
            stdout = b""
            stderr = str(e).encode("utf-8", "replace")
        latency = time.monotonic() - t0
        out_files = {}
        for fp in pathlib.Path(work).rglob("*"):
            if fp.is_file():
                rel = fp.relative_to(work).as_posix()
                data = fp.read_bytes()
                if before.get(rel) != data:
                    out_files[rel] = data
        obs = {"exit": rc, "stdout": stdout, "stderr": stderr, "files": out_files}
        fails = check_assertions(obs, case.get("assertions", []))
        passed = not fails and not timed_out and not crashed
        return {
            "id": case.get("id"),
            "modules": case.get("modules", []),
            "security_metric": case.get("security_metric"),
            "smoke": bool(case.get("smoke")),
            "passed": passed,
            "fails": fails,
            "timed_out": timed_out,
            "crashed": crashed,
            "latency_s": round(latency, 6),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def suite_cases(rid):
    case_dir = OUT / rid / "07_exam" / "grader" / "cases"
    cases = []
    for p in sorted(case_dir.glob("*.json")):
        c = load_json(p)
        if isinstance(c, dict):
            cases.append(c)
    return cases


def summarize_case_results(rid, agent, score, cases, results, build_gate_ok):
    functional_ids = {c.get("id") for c in cases if not c.get("security_metric") and not c.get("smoke")}
    functional = [r for r in results if r["id"] in functional_ids]
    modules = sorted({str(m).upper() for c in cases if c.get("id") in functional_ids for m in c.get("modules", []) if m})
    by_mod = {m: {"passed": 0, "total": 0} for m in modules}
    for r in functional:
        for m in r.get("modules", []):
            mm = str(m).upper()
            if mm in by_mod:
                by_mod[mm]["total"] += 1
                if r.get("passed"):
                    by_mod[mm]["passed"] += 1
    if not build_gate_ok:
        passed_cases = 0
        passed_modules = 0
    else:
        passed_cases = sum(1 for r in functional if r.get("passed"))
        passed_modules = sum(1 for m, v in by_mod.items() if v["total"] and v["passed"] == v["total"])
    total_cases = len(functional)
    total_modules = len(modules)
    return {
        "rid": rid,
        "agent": agent,
        "original_score_build_ok": bool(score.get("build_ok")),
        "original_score_func": score.get(FUNC_KEY),
        "rerun_build_gate_ok": bool(build_gate_ok),
        "functional_passed": passed_cases,
        "functional_total": total_cases,
        "functional_pass_rate": passed_cases / total_cases if total_cases else 0.0,
        "covered_modules": passed_modules,
        "total_modules": total_modules,
        "requirement_coverage": passed_modules / total_modules if total_modules else 0.0,
        "perfect_project": bool(build_gate_ok and total_cases and passed_cases == total_cases),
        "per_module": by_mod,
    }


def run_candidate(task):
    rid, agent, out_dir, timeout, build_mode, use_wrapper = task
    score = load_json(GRADES / rid / agent / "score.json", {}) or {}
    cases = suite_cases(rid)
    functional_total = sum(1 for c in cases if not c.get("security_metric") and not c.get("smoke"))
    modules = sorted({str(m).upper() for c in cases if not c.get("security_metric") and not c.get("smoke")
                      for m in c.get("modules", []) if m})

    cand_dir = pathlib.Path(out_dir) / "case_results" / rid / agent
    summary_path = cand_dir / "summary.json"
    cases_path = cand_dir / "cases.json"
    if summary_path.exists() and cases_path.exists():
        return load_json(summary_path, {})

    if not score.get("build_ok"):
        summary = {
            "rid": rid,
            "agent": agent,
            "original_score_build_ok": False,
            "original_score_func": score.get(FUNC_KEY),
            "rerun_build_gate_ok": False,
            "skipped_reason": "original_build_ok_false_gate_zeroed",
            "functional_passed": 0,
            "functional_total": functional_total,
            "functional_pass_rate": 0.0,
            "covered_modules": 0,
            "total_modules": len(modules),
            "requirement_coverage": 0.0,
            "perfect_project": False,
            "per_module": {m: {"passed": 0, "total": 0} for m in modules},
        }
        write_json(summary_path, summary)
        write_json(cases_path, [])
        return summary

    work = SUBS / rid / agent / "work"
    build_ok, build_msg, launch = prepare_candidate(work, build_mode, use_wrapper)
    if not build_ok or not launch:
        summary = {
            "rid": rid, "agent": agent,
            "original_score_build_ok": True,
            "original_score_func": score.get(FUNC_KEY),
            "rerun_build_gate_ok": False,
            "rerun_error": build_msg or "missing launch",
            "functional_passed": 0,
            "functional_total": functional_total,
            "functional_pass_rate": 0.0,
            "covered_modules": 0,
            "total_modules": len(modules),
            "requirement_coverage": 0.0,
            "perfect_project": False,
            "per_module": {m: {"passed": 0, "total": 0} for m in modules},
        }
        write_json(summary_path, summary)
        write_json(cases_path, [])
        return summary

    results = [run_one_case(c, launch, timeout) for c in cases]
    smoke = [r for r in results if r.get("smoke")]
    gate_ok = (all(r.get("passed") for r in smoke) if smoke else True)
    summary = summarize_case_results(rid, agent, score, cases, results, gate_ok)
    write_json(summary_path, summary)
    write_json(cases_path, results)
    return summary


def aggregate(summaries, agents, out_dir):
    by_agent = {}
    for agent in agents:
        rows = [s for s in summaries if s.get("agent") == agent]
        if not rows:
            continue
        projects = len(rows)
        cases_total = sum(s.get("functional_total", 0) for s in rows)
        cases_passed = sum(s.get("functional_passed", 0) for s in rows)
        mods_total = sum(s.get("total_modules", 0) for s in rows)
        mods_passed = sum(s.get("covered_modules", 0) for s in rows)
        by_agent[agent] = {
            "projects": projects,
            "avg_requirement_coverage": sum(s.get("requirement_coverage", 0.0) for s in rows) / projects if projects else 0.0,
            "module_weighted_requirement_coverage": mods_passed / mods_total if mods_total else 0.0,
            "covered_modules": mods_passed,
            "total_modules": mods_total,
            "test_passed": cases_passed,
            "test_total": cases_total,
            "test_pass_rate": cases_passed / cases_total if cases_total else 0.0,
            "perfect_projects": sum(1 for s in rows if s.get("perfect_project")),
            "rerun_gate_failed_after_original_ok": sum(1 for s in rows if s.get("original_score_build_ok") and not s.get("rerun_build_gate_ok")),
        }
    all_cases = sum(v["test_total"] for v in by_agent.values())
    all_passed = sum(v["test_passed"] for v in by_agent.values())
    result = {
        "agents": by_agent,
        "overall": {
            "projects": sum(v["projects"] for v in by_agent.values()),
            "test_passed": all_passed,
            "test_total": all_cases,
            "test_pass_rate": all_passed / all_cases if all_cases else 0.0,
            "perfect_projects": sum(v["perfect_projects"] for v in by_agent.values()),
        },
    }
    write_json(pathlib.Path(out_dir) / "metrics_summary.json", result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    ap.add_argument("--out-dir", default=str(STATE / "rerun_case_metrics"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("CASE_TIMEOUT", "60")))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--build-mode", choices=["missing", "always"], default="missing")
    ap.add_argument("--wrapper", action="store_true")
    args = ap.parse_args()

    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    rids = sorted(p.name for p in GRADES.iterdir() if p.is_dir() and p.name not in EXCLUDE_REPOS)
    tasks = [(rid, agent, args.out_dir, args.timeout, args.build_mode, args.wrapper)
             for rid in rids for agent in agents
             if (GRADES / rid / agent / "score.json").exists()]
    if args.limit:
        tasks = tasks[:args.limit]

    pathlib.Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    summaries = []
    errors = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_candidate, t): t for t in tasks}
        for fut in cf.as_completed(futs):
            t = futs[fut]
            done += 1
            try:
                summaries.append(fut.result())
            except Exception as e:
                err = {"task": t[:2], "error": repr(e), "traceback": traceback.format_exc()}
                errors.append(err)
            if done % 10 == 0 or done == len(tasks):
                progress = {"done": done, "total": len(tasks), "errors": len(errors), "time": time.time()}
                write_json(pathlib.Path(args.out_dir) / "progress.json", progress)
                print(json.dumps(progress, ensure_ascii=False), flush=True)
    write_json(pathlib.Path(args.out_dir) / "all_project_summaries.json", summaries)
    write_json(pathlib.Path(args.out_dir) / "errors.json", errors)
    result = aggregate(summaries, agents, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
