#!/usr/bin/env python3
import collections
import json
import os
import pathlib
import re

PREFIX = pathlib.Path("/mnt/yangh559")
CODE = PREFIX / "code-bench-v2"
STATE = PREFIX / "chuti-run"
GRADES = STATE / "grades"
EXAMS = STATE / "exams"
SUBS = STATE / "submissions"
LOGS = STATE / "logs"
OUT = CODE / "out"
MANIFEST = CODE / "dataset" / "repo-list.manifest.json"
REPORT_LANG = CODE / "_report_lang.json"

AGENTS = ["claude", "codex", "cursor", "kimi", "agy"]
MAIN = ["claude", "codex", "cursor", "kimi"]
EXCLUDE = {"dosisod-refurb"}
FUNC_KEY = "\u529f\u80fd\u5206"

EXT = {
    ".go": "go", ".py": "python", ".rs": "rust", ".ts": "ts", ".tsx": "ts",
    ".js": "js", ".jsx": "js", ".java": "java", ".cpp": "c++", ".cc": "c++",
    ".cxx": "c++", ".c": "c", ".rb": "ruby", ".cs": "c#", ".php": "php",
    ".kt": "kotlin", ".swift": "swift", ".scala": "scala", ".pl": "perl",
    ".ex": "elixir", ".exs": "elixir", ".ml": "ocaml", ".hs": "haskell",
    ".lua": "lua",
}
SKIP_PARTS = {
    "node_modules", "gomodcache", ".gocache", "target", ".venv", "vendor",
    ".cargo", ".rustup", ".gopath", "_ref", "__pycache__", ".git", "dist",
    "build", ".ref-",
}


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def canon(lang):
    lang = (lang or "").strip().lower()
    return {
        "golang": "go",
        "javascript": "js",
        "typescript": "ts",
        "node": "js",
        "nodejs": "js",
        "node.js": "js",
        "cpp": "c++",
        "csharp": "c#",
        "python3": "python",
    }.get(lang, lang)


def functional_case_count(rid):
    cdir = OUT / rid / "07_exam" / "grader" / "cases"
    if not cdir.is_dir():
        return 0
    n = 0
    modules = set()
    for p in cdir.glob("*.json"):
        c = load_json(p, {})
        if c.get("security_metric") or c.get("smoke"):
            continue
        n += 1
        modules.update(canon(m) or m for m in c.get("modules", []) if m)
    return n


def module_count(rid):
    cdir = OUT / rid / "07_exam" / "grader" / "cases"
    modules = set()
    if cdir.is_dir():
        for p in cdir.glob("*.json"):
            c = load_json(p, {})
            modules.update(str(m).upper() for m in c.get("modules", []) if m)
    return len(modules)


def score_path(rid, agent):
    return GRADES / rid / agent / "score.json"


def log_text(rid, agent):
    p = LOGS / f"grade-{rid}-{agent}.log"
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def classify_build_failure(text):
    low = text.lower()
    if "traceback" in low:
        if "filenotfounderror" in low or "no such file or directory" in low:
            return "grade_crash_missing_file_or_launch"
        if "syntaxerror" in low:
            return "grade_crash_candidate_or_script_syntax"
        return "grade_crash_other"
    if "[build.sh" in low and "非零退出" in text:
        if any(s in low for s in ["npm err", "pnpm", "yarn", "node-gyp"]):
            return "build_script_failed_node"
        if any(s in low for s in ["cargo", "rustc", "error: could not compile"]):
            return "build_script_failed_rust"
        if any(s in low for s in ["go build", "go: ", "package ", "cannot find module"]):
            return "build_script_failed_go"
        if any(s in low for s in ["pip", "python", "module not found", "modulenotfounderror"]):
            return "build_script_failed_python"
        if any(s in low for s in ["network", "timeout", "could not resolve", "connection refused", "certificate"]):
            return "build_script_dependency_or_network"
        return "build_script_failed_other"
    if any(s in low for s in ["command not found", "not found", "no such file or directory", "permission denied"]):
        return "missing_command_file_or_permission"
    if "build complete" in low or "build ok" in low or "finished release" in low:
        return "smoke_or_launch_gate_failed_after_build"
    if len(text.strip()) <= 900:
        return "smoke_or_launch_gate_failed_low_log"
    return "unknown_or_unclassified"


def dominant_language(work):
    cnt = collections.Counter()
    if not work.is_dir():
        return None, 0
    for root, dirs, files in os.walk(work):
        parts = set(pathlib.Path(root).parts)
        if parts & SKIP_PARTS:
            dirs[:] = []
            continue
        for fn in files:
            ext = pathlib.Path(fn).suffix.lower()
            if ext in EXT:
                cnt[EXT[ext]] += 1
    if not cnt:
        return None, 0
    lang, n = cnt.most_common(1)[0]
    return canon(lang), sum(cnt.values())


def main():
    rids = sorted(p.name for p in GRADES.iterdir() if p.is_dir() and p.name not in EXCLUDE)
    case_counts = {rid: functional_case_count(rid) for rid in rids}
    module_counts = {rid: module_count(rid) for rid in rids}
    scored_rids = [rid for rid in rids if case_counts.get(rid, 0) > 0]

    scores = {}
    aggregate = {a: {"projects": 0, "cases": 0, "passed_est": 0, "perfect": 0,
                     "build_fail": 0, "func_sum": 0.0} for a in AGENTS}
    rounding = []
    failures = []
    for rid in scored_rids:
        ncases = case_counts[rid]
        for a in AGENTS:
            sc = load_json(score_path(rid, a))
            if not isinstance(sc, dict):
                continue
            func = float(sc.get(FUNC_KEY, 0) or 0)
            build_ok = bool(sc.get("build_ok"))
            passed = int(round(func * ncases))
            rounding.append(abs(func * ncases - passed))
            aggregate[a]["projects"] += 1
            aggregate[a]["cases"] += ncases
            aggregate[a]["passed_est"] += passed
            aggregate[a]["perfect"] += 1 if build_ok and func >= 0.99995 else 0
            aggregate[a]["build_fail"] += 0 if build_ok else 1
            aggregate[a]["func_sum"] += func
            scores[(rid, a)] = (sc, ncases, passed)
            if not build_ok:
                text = log_text(rid, a)
                failures.append({
                    "rid": rid,
                    "agent": a,
                    "reason": classify_build_failure(text),
                    "log_tail": "\n".join(text.splitlines()[-8:]),
                })

    for a, row in aggregate.items():
        row["pass_rate"] = row["passed_est"] / row["cases"] if row["cases"] else 0
        row["avg_func_unweighted"] = row["func_sum"] / row["projects"] if row["projects"] else 0

    main_tot = {
        "projects": sum(aggregate[a]["projects"] for a in MAIN),
        "cases": sum(aggregate[a]["cases"] for a in MAIN),
        "passed_est": sum(aggregate[a]["passed_est"] for a in MAIN),
    }
    main_tot["pass_rate"] = main_tot["passed_est"] / main_tot["cases"] if main_tot["cases"] else 0

    fail_by_reason = collections.Counter(f["reason"] for f in failures)
    fail_by_agent = collections.Counter(f["agent"] for f in failures)
    main_failures = [f for f in failures if f["agent"] in MAIN]
    main_fail_by_reason = collections.Counter(f["reason"] for f in main_failures)
    main_fail_by_agent = collections.Counter(f["agent"] for f in main_failures)
    fail_samples = {}
    for f in failures:
        fail_samples.setdefault(f["reason"], f)

    manifest = load_json(MANIFEST, [])
    rows = manifest if isinstance(manifest, list) else manifest.get("repos", manifest.get("items", []))
    man = {x.get("id"): x for x in rows if x.get("id")}
    rep = load_json(REPORT_LANG, {}) or {}
    lang_stats = {a: collections.Counter() for a in AGENTS}
    lang_samples = []
    for rid in scored_rids:
        meta = load_json(EXAMS / rid / "meta.json", {}) or {}
        target = canon(meta.get("generation_language"))
        orig = canon((rep.get(rid, {}) or {}).get("orig") or (man.get(rid, {}) or {}).get("_lang"))
        for a in AGENTS:
            work = SUBS / rid / a / "work"
            if not work.is_dir():
                continue
            wrote, nfiles = dominant_language(work)
            if not wrote:
                lang_stats[a]["undetected"] += 1
                continue
            if wrote == target:
                lang_stats[a]["target_ok"] += 1
            elif wrote == orig and orig:
                lang_stats[a]["orig_language_clone_or_violation"] += 1
                lang_samples.append({"rid": rid, "agent": a, "target": target, "orig": orig, "wrote": wrote})
            else:
                lang_stats[a]["wrong_other_language"] += 1
                lang_samples.append({"rid": rid, "agent": a, "target": target, "orig": orig, "wrote": wrote})
            lang_stats[a]["detected"] += 1

    out = {
        "dataset": {
            "graded_repo_dirs": len(rids),
            "repos_with_cases": len(scored_rids),
            "functional_cases_total_unique": sum(case_counts[rid] for rid in scored_rids),
            "modules_total_unique": sum(module_counts[rid] for rid in scored_rids),
            "excluded": sorted(EXCLUDE),
        },
        "main_total": main_tot,
        "by_agent": aggregate,
        "rounding_max_abs_cases": max(rounding) if rounding else 0,
        "build_failures": {
            "total": len(failures),
            "by_agent": dict(fail_by_agent),
            "by_reason": dict(fail_by_reason),
            "main_total": len(main_failures),
            "main_by_agent": dict(main_fail_by_agent),
            "main_by_reason": dict(main_fail_by_reason),
            "samples": fail_samples,
        },
        "language": {
            "by_agent": {a: dict(lang_stats[a]) for a in AGENTS},
            "samples": lang_samples[:40],
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
