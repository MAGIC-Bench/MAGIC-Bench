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

AGENTS = ["claude", "codex", "cursor", "kimi"]
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
IDENTITY_FILES = {
    "cargo.toml", "cargo.lock", "go.mod", "go.sum", "package.json", "package-lock.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "gemfile", "gemfile.lock",
    "composer.json", "pom.xml", "build.gradle", "makefile", "cmakelists.txt",
}
SKIP_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".gocache", ".gomodcache", ".cargo-home", ".rustup-home",
    ".cargo", ".gopath", "vendor", "coverage", ".next", ".cache", ".yarn", ".idea",
}


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


def iter_files(base):
    if not base.is_dir():
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".ref")]
        for name in files:
            p = pathlib.Path(root) / name
            rel = p.relative_to(base).as_posix()
            low_parts = {part.lower() for part in pathlib.Path(rel).parts}
            if low_parts & SKIP_DIRS:
                continue
            yield p, rel


def source_files(base):
    for p, rel in iter_files(base):
        if p.suffix.lower() in SOURCE_EXT:
            yield p, rel


def file_sha(path):
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def dominant_language(work):
    cnt = collections.Counter()
    for p, _ in source_files(work):
        cnt[canon(EXT_LANG.get(p.suffix.lower()))] += 1
    if not cnt:
        return None, 0, {}
    return cnt.most_common(1)[0][0], sum(cnt.values()), dict(cnt)


def build_hash_index(repo):
    idx = {}
    rel_by_hash = collections.defaultdict(list)
    for p, rel in source_files(repo):
        sha = file_sha(p)
        if not sha:
            continue
        idx[rel] = sha
        rel_by_hash[sha].append(rel)
    return idx, rel_by_hash


def line_fingerprint(path):
    vals = set()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return vals
    for line in text.splitlines():
        s = re.sub(r"\s+", " ", line.strip())
        if len(s) < 12 or s.startswith("//") or s.startswith("#") or s.startswith("*"):
            continue
        vals.add(hashlib.sha1(s.encode("utf-8")).hexdigest())
    return vals


def repo_line_index(repo, lang):
    idx = collections.defaultdict(list)
    for p, rel in source_files(repo):
        if canon(EXT_LANG.get(p.suffix.lower())) != lang:
            continue
        for fp in line_fingerprint(p):
            idx[fp].append(rel)
    return idx


def top_line_overlap(candidate, repo, lang, max_files=8):
    repo_idx = repo_line_index(repo, lang)
    out = []
    if not repo_idx:
        return out
    for p, rel in source_files(candidate):
        if canon(EXT_LANG.get(p.suffix.lower())) != lang:
            continue
        fps = line_fingerprint(p)
        if len(fps) < 8:
            continue
        counts = collections.Counter()
        for fp in fps:
            for r in repo_idx.get(fp, []):
                counts[r] += 1
        if not counts:
            continue
        best_rel, common = counts.most_common(1)[0]
        ratio = common / max(len(fps), 1)
        if common >= 8 and ratio >= 0.35:
            out.append({"candidate": rel, "original": best_rel, "common_lines": common, "ratio": round(ratio, 3)})
    out.sort(key=lambda x: (x["common_lines"], x["ratio"]), reverse=True)
    return out[:max_files]


def identity_hits(work, rid, original_repo):
    hits = []
    tokens = set()
    repo_full = original_repo or rid
    for part in re.split(r"[-_/]", rid.lower()):
        if len(part) >= 4:
            tokens.add(part)
    for part in re.split(r"[-_/]", repo_full.lower()):
        if len(part) >= 4:
            tokens.add(part)
    tokens.add(rid.lower())
    if original_repo:
        tokens.add(original_repo.lower())
    for p, rel in iter_files(work):
        low_rel = rel.lower()
        if any(tok in low_rel for tok in tokens):
            hits.append({"where": "path", "rel": rel})
            continue
        if p.name.lower() in IDENTITY_FILES or p.name.lower().startswith("readme"):
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore").lower()[:20000]
            except Exception:
                txt = ""
            found = [tok for tok in tokens if tok and tok in txt]
            if found:
                hits.append({"where": "file", "rel": rel, "tokens": found[:5]})
    return hits[:20]


def suspicious_dirs(work):
    names = []
    for p in work.rglob("*"):
        if not p.is_dir():
            continue
        rel = p.relative_to(work).as_posix()
        low = p.name.lower()
        if low in {"_ref", "ref", "upstream", "_upstream", "original", "source", "vendor"} or low.startswith("_ref"):
            names.append(rel)
    return names[:20]


def main():
    manifest = load_json(MANIFEST, [])
    rows = manifest if isinstance(manifest, list) else manifest.get("repos", manifest.get("items", []))
    man = {x.get("id"): x for x in rows if x.get("id")}
    report_lang = load_json(REPORT_LANG, {}) or {}

    repo_hash_cache = {}
    results = []

    for rid_dir in sorted(GRADES.iterdir()):
        if not rid_dir.is_dir() or rid_dir.name in EXCLUDE:
            continue
        rid = rid_dir.name
        meta = load_json(EXAMS / rid / "meta.json", {}) or {}
        target = canon(meta.get("generation_language"))
        orig = canon((report_lang.get(rid, {}) or {}).get("orig") or (man.get(rid, {}) or {}).get("_lang"))
        repo_full = (man.get(rid, {}) or {}).get("_repo", rid)
        repo_dir = REPOS / rid
        if not repo_dir.is_dir():
            continue
        if rid not in repo_hash_cache:
            repo_hash_cache[rid] = build_hash_index(repo_dir)
        repo_hash, repo_rel_by_hash = repo_hash_cache[rid]

        for agent in AGENTS:
            score = load_json(rid_dir / agent / "score.json", {})
            work = SUBS / rid / agent / "work"
            wrote, nfiles, lang_counts = dominant_language(work)
            if wrote == target or wrote is None:
                continue

            exact = []
            same_path_exact = []
            for p, rel in source_files(work):
                sha = file_sha(p)
                if not sha:
                    continue
                if repo_hash.get(rel) == sha:
                    same_path_exact.append(rel)
                elif sha in repo_rel_by_hash:
                    exact.append({"candidate": rel, "original": repo_rel_by_hash[sha][:5]})

            overlaps = top_line_overlap(work, repo_dir, wrote)
            ids = identity_hits(work, rid, repo_full)
            sdirs = suspicious_dirs(work)

            evidence = "weak"
            reasons = []
            if same_path_exact or len(exact) >= 3:
                evidence = "strong"
                reasons.append("candidate_contains_exact_original_source_files")
            if sdirs:
                evidence = "strong"
                reasons.append("candidate_contains_ref_or_upstream_dir")
            if ids:
                if evidence != "strong":
                    evidence = "medium"
                reasons.append("candidate_contains_original_identity_tokens")
            if overlaps:
                if evidence == "weak":
                    evidence = "medium"
                reasons.append("candidate_source_line_overlap_with_original")
            if wrote == orig:
                reasons.append("dominant_language_equals_original_language")
            else:
                reasons.append("dominant_language_is_wrong_but_not_original")
            if float(score.get(FUNC_KEY, 0) or 0) >= 0.95 and wrote == orig:
                if evidence != "strong":
                    evidence = "medium"
                reasons.append("high_functional_score_in_original_language")

            results.append({
                "rid": rid,
                "repo_full": repo_full,
                "agent": agent,
                "target": target,
                "orig": orig,
                "wrote": wrote,
                "lang_counts": lang_counts,
                "build_ok": score.get("build_ok"),
                "func": score.get(FUNC_KEY),
                "evidence": evidence,
                "reasons": reasons,
                "same_path_exact_count": len(same_path_exact),
                "same_path_exact_sample": same_path_exact[:10],
                "exact_diff_path_count": len(exact),
                "exact_diff_path_sample": exact[:8],
                "line_overlap_sample": overlaps,
                "identity_hits": ids,
                "suspicious_dirs": sdirs,
            })

    by_evidence = collections.Counter(r["evidence"] for r in results)
    by_agent = collections.Counter(r["agent"] for r in results)
    by_kind = collections.Counter("orig_language" if r["wrote"] == r["orig"] else "other_wrong_language" for r in results)
    print(json.dumps({
        "total_flagged": len(results),
        "by_evidence": dict(by_evidence),
        "by_agent": dict(by_agent),
        "by_kind": dict(by_kind),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
