#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shlex
import subprocess
import tempfile
import time
from collections import defaultdict

PREFIX = pathlib.Path("/mnt/yangh559")
CODE = PREFIX / "code-bench-v2"
STATE = PREFIX / "chuti-run"
GRADES = STATE / "grades"
SUBS = STATE / "submissions"
EXAMS = STATE / "exams"

DEFAULT_AGENTS = ["claude", "codex", "cursor", "kimi"]
EXCLUDE_REPOS = {"dosisod-refurb"}


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def contract_path(rid):
    candidates = [
        EXAMS / rid / "candidate" / "02_cli-contract.json",
        CODE / "out" / rid / "07_exam" / "candidate" / "02_cli-contract.json",
    ]
    return next((p for p in candidates if p.exists()), None)


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


def split_form(form, binary):
    try:
        argv = shlex.split(str(form))
    except Exception:
        return None
    if not argv:
        return None
    if argv[0] in {binary, "app"}:
        argv = argv[1:]
    if any(any(ch in tok for ch in "<>[]...") for tok in argv):
        return None
    return argv


def declared_flags(contract):
    flags = contract.get("flags") or []
    longs, shorts = [], []
    for f in flags:
        if isinstance(f, dict):
            long = str(f.get("long") or "").strip().lstrip("-")
            short = str(f.get("short") or "").strip().lstrip("-")
        else:
            text = str(f).strip()
            long = text.lstrip("-") if text.startswith("--") else ""
            short = text.lstrip("-") if re.match(r"^-[A-Za-z0-9]$", text) else ""
        if long:
            longs.append(long)
        if short and short.lower() != "null":
            shorts.append(short)
    return sorted(set(longs)), sorted(set(shorts))


def explicit_forms(contract, action_name):
    action = (contract.get("actions") or {}).get(action_name) or {}
    if not isinstance(action, dict):
        return []
    return action.get("forms") or []


def make_probe_plan(contract):
    binary = str(contract.get("binary") or "app")
    long_flags, short_flags = declared_flags(contract)
    actions = contract.get("actions") or {}
    probes = []
    seen_run = set()

    def add_run(name, argv, expect):
        key = tuple(argv)
        if key in seen_run:
            return
        seen_run.add(key)
        probes.append({"kind": "run", "name": name, "argv": argv, "expect": expect})

    add_run("help_long", ["--help"], "help_success")
    if "h" in short_flags:
        add_run("help_short", ["-h"], "help_success")
    for form in explicit_forms(contract, "help"):
        argv = split_form(form, binary)
        if argv:
            add_run("help_form:" + " ".join(argv), argv, "help_success")

    has_version = "version" in actions or "version" in long_flags
    if has_version:
        add_run("version_long", ["--version"], "version_success")
    if "V" in short_flags or "v" in short_flags:
        # Prefer -V when present; many CLIs reserve -v for verbose, so only add
        # -v when the contract explicitly maps it to version via forms.
        if "V" in short_flags:
            add_run("version_short", ["-V"], "version_success")
    for form in explicit_forms(contract, "version"):
        argv = split_form(form, binary)
        if argv:
            add_run("version_form:" + " ".join(argv), argv, "version_success")

    add_run("unknown_option_rejected", ["--__codebench_invalid_option__"], "nonzero")

    for flag in long_flags:
        probes.append({"kind": "help_contains", "name": f"help_contains_long:--{flag}", "needle": f"--{flag}"})
    for flag in short_flags:
        probes.append({"kind": "help_contains", "name": f"help_contains_short:-{flag}", "needle": f"-{flag}"})
    for action_name, spec in sorted(actions.items()):
        if action_name in {"precedence", "help", "version"}:
            continue
        if isinstance(spec, dict):
            probes.append({"kind": "help_contains", "name": f"help_contains_action:{action_name}", "needle": action_name})
    return probes


def run_candidate(launch, argv, timeout):
    work = tempfile.mkdtemp(prefix="cli_contract_")
    env = dict(os.environ, TZ="UTC", LC_ALL="C", NO_COLOR="1")
    try:
        try:
            p = subprocess.run([*launch, *argv], capture_output=True, cwd=work, env=env, timeout=timeout)
            return {
                "exit": p.returncode,
                "stdout": p.stdout.decode("utf-8", "replace"),
                "stderr": p.stderr.decode("utf-8", "replace"),
                "timed_out": False,
                "crashed": p.returncode < 0,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "exit": 124,
                "stdout": (e.stdout or b"").decode("utf-8", "replace"),
                "stderr": (e.stderr or b"").decode("utf-8", "replace"),
                "timed_out": True,
                "crashed": False,
            }
        except Exception as e:
            return {"exit": 127, "stdout": "", "stderr": repr(e), "timed_out": False, "crashed": True}
    finally:
        try:
            pathlib.Path(work).rmdir()
        except Exception:
            pass


def check_run(obs, expect):
    text = (obs.get("stdout") or "") + "\n" + (obs.get("stderr") or "")
    low = text.lower()
    if expect == "help_success":
        return obs["exit"] == 0 and bool(text.strip()) and (
            "usage" in low or "options" in low or "commands" in low or "help" in low
        )
    if expect == "version_success":
        return obs["exit"] == 0 and bool(text.strip()) and not obs.get("timed_out")
    if expect == "nonzero":
        return obs["exit"] != 0 and not obs.get("timed_out")
    return False


def score_one(task):
    rid, agent, out_dir, timeout = task
    score = load_json(GRADES / rid / agent / "score.json", {}) or {}
    cpath = contract_path(rid)
    contract = load_json(cpath, {}) if cpath else {}
    probes = make_probe_plan(contract) if contract else []
    total = len(probes)
    result_dir = pathlib.Path(out_dir) / "case_results" / rid / agent
    summary_path = result_dir / "summary.json"
    detail_path = result_dir / "probes.json"
    if summary_path.exists():
        return load_json(summary_path, {})

    base = {
        "rid": rid,
        "agent": agent,
        "build_ok": bool(score.get("build_ok")),
        "contract_path": str(cpath) if cpath else None,
        "probe_total": total,
        "probe_passed": 0,
        "interface_compliance": 0.0,
        "fully_compliant": False,
    }
    if not probes:
        summary = {**base, "error": "missing_or_empty_cli_contract"}
        write_json(summary_path, summary)
        write_json(detail_path, [])
        return summary
    if not score.get("build_ok"):
        details = [{**p, "passed": False, "skipped": "build_failed"} for p in probes]
        summary = {**base, "error": "build_failed"}
        write_json(summary_path, summary)
        write_json(detail_path, details)
        return summary

    launch = fixed_launch(SUBS / rid / agent / "work")
    if not launch:
        details = [{**p, "passed": False, "skipped": "missing_launch"} for p in probes]
        summary = {**base, "error": "missing_launch"}
        write_json(summary_path, summary)
        write_json(detail_path, details)
        return summary

    details = []
    run_outputs = {}
    help_text = ""
    for p in probes:
        if p["kind"] != "run":
            continue
        obs = run_candidate(launch, p["argv"], timeout)
        passed = check_run(obs, p["expect"])
        item = {**p, "passed": passed, "exit": obs["exit"], "timed_out": obs["timed_out"],
                "stdout_preview": obs["stdout"][:500], "stderr_preview": obs["stderr"][:500]}
        details.append(item)
        run_outputs[p["name"]] = obs
        if p["expect"] == "help_success" and not help_text and obs["exit"] == 0:
            help_text = (obs.get("stdout") or "") + "\n" + (obs.get("stderr") or "")

    for p in probes:
        if p["kind"] != "help_contains":
            continue
        passed = p["needle"] in help_text
        details.append({**p, "passed": passed})

    passed = sum(1 for d in details if d.get("passed"))
    summary = {
        **base,
        "probe_passed": passed,
        "interface_compliance": passed / total if total else 0.0,
        "fully_compliant": bool(total and passed == total),
    }
    write_json(summary_path, summary)
    write_json(detail_path, details)
    return summary


def aggregate(rows, agents, out_dir):
    out = {"agents": {}, "overall": {}}
    for agent in agents:
        rs = [r for r in rows if r.get("agent") == agent]
        build_ok_rs = [r for r in rs if r.get("build_ok")]
        passed = sum(r.get("probe_passed", 0) for r in rs)
        total = sum(r.get("probe_total", 0) for r in rs)
        ok_passed = sum(r.get("probe_passed", 0) for r in build_ok_rs)
        ok_total = sum(r.get("probe_total", 0) for r in build_ok_rs)
        out["agents"][agent] = {
            "projects": len(rs),
            "build_ok_projects": len(build_ok_rs),
            "build_failed_projects": len(rs) - len(build_ok_rs),
            "probe_passed": passed,
            "probe_total": total,
            "interface_compliance_all": passed / total if total else 0.0,
            "probe_passed_build_ok_only": ok_passed,
            "probe_total_build_ok_only": ok_total,
            "interface_compliance_build_ok_only": ok_passed / ok_total if ok_total else 0.0,
            "avg_project_compliance_all": sum(r.get("interface_compliance", 0.0) for r in rs) / len(rs) if rs else 0.0,
            "avg_project_compliance_build_ok_only": (
                sum(r.get("interface_compliance", 0.0) for r in build_ok_rs) / len(build_ok_rs)
                if build_ok_rs else 0.0
            ),
            "fully_compliant_projects": sum(1 for r in rs if r.get("fully_compliant")),
        }
    all_rows = [r for r in rows if r.get("agent") in agents]
    all_ok = [r for r in all_rows if r.get("build_ok")]
    passed = sum(r.get("probe_passed", 0) for r in all_rows)
    total = sum(r.get("probe_total", 0) for r in all_rows)
    ok_passed = sum(r.get("probe_passed", 0) for r in all_ok)
    ok_total = sum(r.get("probe_total", 0) for r in all_ok)
    out["overall"] = {
        "projects": len(all_rows),
        "build_ok_projects": len(all_ok),
        "build_failed_projects": len(all_rows) - len(all_ok),
        "probe_passed": passed,
        "probe_total": total,
        "interface_compliance_all": passed / total if total else 0.0,
        "probe_passed_build_ok_only": ok_passed,
        "probe_total_build_ok_only": ok_total,
        "interface_compliance_build_ok_only": ok_passed / ok_total if ok_total else 0.0,
        "fully_compliant_projects": sum(1 for r in all_rows if r.get("fully_compliant")),
    }
    write_json(pathlib.Path(out_dir) / "interface_compliance_summary.json", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    ap.add_argument("--out-dir", default=str(STATE / "cli_interface_compliance"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    rids = sorted(p.name for p in GRADES.iterdir() if p.is_dir() and p.name not in EXCLUDE_REPOS)
    tasks = [(rid, agent, args.out_dir, args.timeout)
             for rid in rids for agent in agents
             if (GRADES / rid / agent / "score.json").exists()]
    if args.limit:
        tasks = tasks[:args.limit]
    pathlib.Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    rows = []
    errors = []
    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(score_one, t): t for t in tasks}
        for fut in cf.as_completed(futs):
            done += 1
            try:
                rows.append(fut.result())
            except Exception as e:
                errors.append({"task": futs[fut][:2], "error": repr(e)})
            if done % 20 == 0 or done == len(tasks):
                progress = {"done": done, "total": len(tasks), "errors": len(errors), "elapsed_s": time.time() - t0}
                write_json(pathlib.Path(args.out_dir) / "progress.json", progress)
                print(json.dumps(progress), flush=True)
    write_json(pathlib.Path(args.out_dir) / "all_project_interface_summaries.json", rows)
    write_json(pathlib.Path(args.out_dir) / "errors.json", errors)
    print(json.dumps(aggregate(rows, agents, args.out_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
