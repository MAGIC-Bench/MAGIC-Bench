#!/usr/bin/env python3
import collections
import hashlib
import json
import os
import pathlib
import re

ROOT = pathlib.Path("/mnt/yangh559/code-bench-v2")
STATE = pathlib.Path("/mnt/yangh559/chuti-run")
REPOS = ROOT / "repos"
GRADES = STATE / "grades"
EXAMS = STATE / "exams"
SUBS = STATE / "submissions"
MANIFEST = ROOT / "dataset" / "repo-list.manifest.json"
REPORT_LANG = ROOT / "_report_lang.json"

AGENTS = ["claude", "codex", "cursor", "kimi", "agy"]
MAIN = {"claude", "codex", "cursor", "kimi"}
EXCLUDE = {"dosisod-refurb"}
FUNC_KEY = "\u529f\u80fd\u5206"

EXT_LANG = {
    ".go": "go", ".py": "python", ".rs": "rust", ".ts": "ts", ".tsx": "ts",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".java": "java", ".cpp": "c++", ".cc": "c++", ".cxx": "c++", ".c": "c",
    ".h": "c", ".hpp": "c++", ".rb": "ruby", ".cs": "c#", ".php": "php",
    ".kt": "kotlin", ".swift": "swift", ".scala": "scala", ".pl": "perl",
    ".ex": "elixir", ".exs": "elixir", ".ml": "ocaml", ".hs": "haskell",
    ".lua": "lua",
}
SOURCE_EXT = set(EXT_LANG)
SKIP_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".gocache", ".gomodcache", ".cargo-home", ".rustup-home",
    ".cargo", ".gopath", "vendor", "coverage", ".next", ".cache", ".yarn", ".idea",
}
SUSPICIOUS_DIRS = {"_ref", "ref", "upstream", "_upstream", "original", "_original"}
TEXT_CHECK_NAMES = {"readme", "readme.md", "license", "license.md", "cargo.toml", "go.mod", "package.json", "pyproject.toml", "setup.py", "gemfile"}


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def canon(lang):
    lang = (lang or "").strip().lower()
    return {
        "golang": "go", "javascript": "js", "typescript": "ts",
        "node": "js", "nodejs": "js", "node.js": "js",
        "cpp": "c++", "csharp": "c#", "python3": "python",
    }.get(lang, lang)


def iter_files(base, include_suspicious=False):
    if not base.is_dir():
        return
    for root, dirs, files in os.walk(base):
        keep = []
        for d in dirs:
            low = d.lower()
            if low in SKIP_DIRS:
                continue
            if low in SUSPICIOUS_DIRS and not include_suspicious:
                continue
            keep.append(d)
        dirs[:] = keep
        for name in files:
            p = pathlib.Path(root) / name
            yield p, p.relative_to(base).as_posix()


def source_files(base):
    for p, rel in iter_files(base):
        if p.suffix.lower() in SOURCE_EXT:
            yield p, rel


def dominant_language(work):
    cnt = collections.Counter()
    for p, _ in source_files(work):
        cnt[canon(EXT_LANG.get(p.suffix.lower()))] += 1
    if not cnt:
        return None, 0, {}
    return cnt.most_common(1)[0][0], sum(cnt.values()), dict(cnt)


def sha(path):
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def line_set(path):
    out = set()
    try:
        if path.stat().st_size > 1_000_000:
            return out
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for line in text.splitlines():
        s = re.sub(r"\s+", " ", line.strip())
        if len(s) < 16 or s.startswith(("//", "#", "*", "/*", "*/")):
            continue
        out.add(hashlib.sha1(s.encode()).hexdigest())
    return out


def package_identity(base):
    out = {}
    go = base / "go.mod"
    if go.exists():
        m = re.search(r"^module\s+(.+)$", go.read_text(errors="ignore"), re.M)
        if m:
            out["go_module"] = m.group(1).strip()
    pkg = base / "package.json"
    if pkg.exists():
        j = load_json(pkg, {})
        if isinstance(j, dict) and j.get("name"):
            out["npm_name"] = j.get("name")
    cargo = base / "Cargo.toml"
    if cargo.exists():
        try:
            text = cargo.read_text(errors="ignore")
            m = re.search(r"(?ms)^\s*\[package\].*?^\s*name\s*=\s*[\"']([^\"']+)[\"']", text)
            if m:
                out["cargo_name"] = m.group(1)
        except Exception:
            pass
    pyproject = base / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(errors="ignore")
            m = re.search(r"(?ms)^\s*\[project\].*?^\s*name\s*=\s*[\"']([^\"']+)[\"']", text)
            if m:
                out["python_project"] = m.group(1)
            m = re.search(r"(?ms)^\s*\[tool\.poetry\].*?^\s*name\s*=\s*[\"']([^\"']+)[\"']", text)
            if m:
                out["poetry_name"] = m.group(1)
        except Exception:
            pass
    return out


def tokens_for(rid, repo_full):
    toks = set()
    for text in [rid, repo_full or ""]:
        low = text.lower()
        toks.add(low)
        for part in re.split(r"[-_/.\s]+", low):
            if len(part) >= 4:
                toks.add(part)
    return {t for t in toks if t}


def identity_hits(work, toks):
    hits = []
    for p, rel in iter_files(work, include_suspicious=False):
        low_rel = rel.lower()
        rel_hits = [t for t in toks if t in low_rel]
        if rel_hits:
            hits.append({"where": "path", "rel": rel, "tokens": rel_hits[:4]})
            continue
        if p.name.lower() in TEXT_CHECK_NAMES or p.suffix.lower() in SOURCE_EXT:
            try:
                if p.stat().st_size > 400_000:
                    continue
                txt = p.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            found = [t for t in toks if t in txt]
            if found:
                hits.append({"where": "file", "rel": rel, "tokens": found[:4]})
    return hits[:20]


def suspicious_dirs(work):
    out = []
    if not work.is_dir():
        return out
    for root, dirs, _files in os.walk(work):
        keep = []
        for d in dirs:
            low = d.lower()
            p = pathlib.Path(root) / d
            if low in SUSPICIOUS_DIRS:
                out.append(p.relative_to(work).as_posix())
                continue
            if low in SKIP_DIRS:
                continue
            keep.append(d)
        dirs[:] = keep
    return out[:20]


def same_relative_evidence(work, repo, lang):
    same = []
    exact = []
    overlap = []
    for p, rel in source_files(work):
        if canon(EXT_LANG.get(p.suffix.lower())) != lang:
            continue
        rp = repo / rel
        if not rp.exists() or not rp.is_file():
            continue
        same.append(rel)
        hp, hr = sha(p), sha(rp)
        if hp and hp == hr:
            exact.append(rel)
            continue
        a, b = line_set(p), line_set(rp)
        if len(a) >= 8 and b:
            common = len(a & b)
            ratio = common / len(a)
            if common >= 8 and ratio >= 0.35:
                overlap.append({"rel": rel, "common_lines": common, "ratio": round(ratio, 3)})
    return same[:20], exact[:20], overlap[:10]


def main():
    manifest = load_json(MANIFEST, [])
    rows = manifest if isinstance(manifest, list) else manifest.get("repos", manifest.get("items", []))
    man = {x.get("id"): x for x in rows if x.get("id")}
    report_lang = load_json(REPORT_LANG, {}) or {}
    results = []

    for rid_dir in sorted(GRADES.iterdir()):
        rid = rid_dir.name
        if not rid_dir.is_dir() or rid in EXCLUDE:
            continue
        repo = REPOS / rid
        if not repo.is_dir():
            continue
        meta = load_json(EXAMS / rid / "meta.json", {}) or {}
        target = canon(meta.get("generation_language"))
        orig = canon((report_lang.get(rid, {}) or {}).get("orig") or (man.get(rid, {}) or {}).get("_lang"))
        repo_full = (man.get(rid, {}) or {}).get("_repo", rid)
        toks = tokens_for(rid, repo_full)
        repo_pkg = package_identity(repo)

        for agent in AGENTS:
            score = load_json(rid_dir / agent / "score.json", {})
            work = SUBS / rid / agent / "work"
            wrote, _nfiles, lang_counts = dominant_language(work)
            if not wrote or wrote == target:
                continue
            work_pkg = package_identity(work)
            sdirs = suspicious_dirs(work)
            ids = identity_hits(work, toks)
            same, exact, overlap = same_relative_evidence(work, repo, wrote) if wrote == orig else ([], [], [])
            pkg_matches = {k: work_pkg[k] for k in set(work_pkg) & set(repo_pkg) if str(work_pkg[k]).lower() == str(repo_pkg[k]).lower()}
            func = float(score.get(FUNC_KEY, 0) or 0)

            evidence = "weak"
            reasons = []
            if wrote == orig:
                reasons.append("dominant_language_equals_original_language")
            else:
                reasons.append("dominant_language_wrong_but_not_original")
            if sdirs:
                evidence = "strong"
                reasons.append("contains_ref_or_upstream_directory")
            if exact:
                evidence = "strong"
                reasons.append("same_relative_source_files_exactly_match_original")
            if overlap:
                evidence = "strong" if any(x["ratio"] >= 0.75 for x in overlap) else "medium"
                reasons.append("same_relative_source_files_overlap_original")
            if pkg_matches:
                evidence = "strong"
                reasons.append("package_or_module_identity_matches_original")
            if ids:
                if evidence == "weak":
                    evidence = "medium"
                reasons.append("contains_original_identity_tokens")
            if len(same) >= 5:
                if evidence == "weak":
                    evidence = "medium"
                reasons.append("many_same_relative_source_paths_as_original")
            if func >= 0.95 and wrote == orig:
                if evidence == "weak":
                    evidence = "medium"
                reasons.append("high_functional_score_in_original_language")

            results.append({
                "rid": rid,
                "repo_full": repo_full,
                "agent": agent,
                "main_agent": agent in MAIN,
                "target": target,
                "orig": orig,
                "wrote": wrote,
                "func": score.get(FUNC_KEY),
                "build_ok": score.get("build_ok"),
                "lang_counts": lang_counts,
                "evidence": evidence,
                "reasons": reasons,
                "package_matches": pkg_matches,
                "candidate_package_identity": work_pkg,
                "original_package_identity": repo_pkg,
                "suspicious_dirs": sdirs,
                "identity_hits": ids,
                "same_relative_paths": same,
                "exact_same_relative_files": exact,
                "same_relative_line_overlap": overlap,
            })

    main_results = [r for r in results if r["main_agent"]]
    print(json.dumps({
        "total_detected_wrong_language": len(results),
        "main_detected_wrong_language": len(main_results),
        "main_by_evidence": dict(collections.Counter(r["evidence"] for r in main_results)),
        "main_by_agent": dict(collections.Counter(r["agent"] for r in main_results)),
        "main_by_kind": dict(collections.Counter("orig_language" if r["wrote"] == r["orig"] else "other_wrong_language" for r in main_results)),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
