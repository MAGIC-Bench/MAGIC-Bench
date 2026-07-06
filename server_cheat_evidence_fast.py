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
IDENTITY_FILES = {
    "cargo.toml", "cargo.lock", "go.mod", "go.sum", "package.json", "package-lock.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "gemfile", "gemfile.lock",
    "composer.json", "pom.xml", "build.gradle", "makefile", "cmakelists.txt", "readme.md",
    "readme", "license", "license.md",
}
SKIP_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".gocache", ".gomodcache", ".cargo-home", ".rustup-home",
    ".cargo", ".gopath", "vendor", "coverage", ".next", ".cache", ".yarn", ".idea",
    "_ref", "ref", "upstream", "_upstream", "original", "source", "_original",
}
SUSPICIOUS_DIR_NAMES = {"_ref", "ref", "upstream", "_upstream", "original", "source", "_original"}


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
            if {x.lower() for x in pathlib.Path(rel).parts} & SKIP_DIRS:
                continue
            yield p, rel


def source_files(base):
    for p, rel in iter_files(base):
        if p.suffix.lower() in SOURCE_EXT:
            yield p, rel


def sha256_file(path):
    try:
        if path.stat().st_size > 2_000_000:
            return None
        h = hashlib.sha256()
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


def repo_hashes(repo):
    by_hash = collections.defaultdict(list)
    rels = set()
    base_names = collections.Counter()
    for p, rel in source_files(repo):
        rels.add(rel)
        base_names[p.name] += 1
        h = sha256_file(p)
        if h:
            by_hash[h].append(rel)
    return by_hash, rels, base_names


def norm_line(line):
    s = re.sub(r"\s+", " ", line.strip())
    if len(s) < 16:
        return None
    if s.startswith(("//", "#", "*", "/*", "*/")):
        return None
    if s in {"{", "}", "};"}:
        return None
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def file_line_fps(path):
    out = set()
    try:
        if path.stat().st_size > 1_000_000:
            return out
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for line in text.splitlines():
        fp = norm_line(line)
        if fp:
            out.add(fp)
    return out


def repo_line_set(repo, lang):
    fps = set()
    for p, _ in source_files(repo):
        if canon(EXT_LANG.get(p.suffix.lower())) == lang:
            fps.update(file_line_fps(p))
    return fps


def overlap_samples(work, repo_fps, lang):
    samples = []
    if not repo_fps:
        return samples
    for p, rel in source_files(work):
        if canon(EXT_LANG.get(p.suffix.lower())) != lang:
            continue
        fps = file_line_fps(p)
        if len(fps) < 10:
            continue
        common = len(fps & repo_fps)
        ratio = common / len(fps)
        if common >= 10 and ratio >= 0.35:
            samples.append({"file": rel, "common_lines": common, "ratio": round(ratio, 3)})
    samples.sort(key=lambda x: (x["common_lines"], x["ratio"]), reverse=True)
    return samples[:10]


def token_set(rid, repo_full):
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
    for p, rel in iter_files(work):
        low_rel = rel.lower()
        rel_hits = [t for t in toks if t in low_rel]
        if rel_hits:
            hits.append({"where": "path", "rel": rel, "tokens": rel_hits[:5]})
            continue
        if p.name.lower() in IDENTITY_FILES or p.suffix.lower() in SOURCE_EXT:
            try:
                if p.stat().st_size > 500_000:
                    continue
                txt = p.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            found = [t for t in toks if t in txt]
            if found:
                hits.append({"where": "file", "rel": rel, "tokens": found[:5]})
    return hits[:30]


def suspicious_dirs(work):
    out = []
    if not work.is_dir():
        return out
    for root, dirs, _files in os.walk(work):
        keep = []
        for d in dirs:
            low = d.lower()
            p = pathlib.Path(root) / d
            if low in SUSPICIOUS_DIR_NAMES:
                out.append(p.relative_to(work).as_posix())
                continue
            if low in SKIP_DIRS:
                continue
            keep.append(d)
        dirs[:] = keep
    return out[:20]


def main():
    manifest = load_json(MANIFEST, [])
    rows = manifest if isinstance(manifest, list) else manifest.get("repos", manifest.get("items", []))
    man = {x.get("id"): x for x in rows if x.get("id")}
    report_lang = load_json(REPORT_LANG, {}) or {}

    hash_cache = {}
    line_cache = {}
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
        toks = token_set(rid, repo_full)

        if rid not in hash_cache:
            hash_cache[rid] = repo_hashes(repo)
        repo_by_hash, repo_rels, repo_basenames = hash_cache[rid]

        for agent in AGENTS:
            score = load_json(rid_dir / agent / "score.json", {})
            work = SUBS / rid / agent / "work"
            wrote, nfiles, lang_counts = dominant_language(work)
            if not wrote or wrote == target:
                continue

            exact = []
            same_rel = []
            uncommon_name_matches = []
            for p, rel in source_files(work):
                h = sha256_file(p)
                if h and h in repo_by_hash:
                    exact.append({"candidate": rel, "original": repo_by_hash[h][:5]})
                if rel in repo_rels:
                    same_rel.append(rel)
                if repo_basenames[p.name] == 1 and len(p.name) >= 8:
                    uncommon_name_matches.append(rel)

            overlaps = []
            if wrote == orig:
                key = (rid, wrote)
                if key not in line_cache:
                    line_cache[key] = repo_line_set(repo, wrote)
                overlaps = overlap_samples(work, line_cache[key], wrote)

            ids = identity_hits(work, toks)
            sdirs = suspicious_dirs(work)
            func = float(score.get(FUNC_KEY, 0) or 0)

            reasons = []
            evidence = "weak"
            if wrote == orig:
                reasons.append("dominant_language_equals_original_language")
            else:
                reasons.append("dominant_language_wrong_but_not_original")
            if exact:
                evidence = "strong"
                reasons.append("exact_source_file_hash_matches_original")
            if sdirs:
                evidence = "strong"
                reasons.append("contains_ref_upstream_original_directory")
            if overlaps:
                evidence = "strong" if any(x["ratio"] >= 0.75 for x in overlaps) else max(evidence, "medium", key=["weak","medium","strong"].index)
                reasons.append("source_line_fingerprint_overlap_with_original")
            if ids:
                if evidence == "weak":
                    evidence = "medium"
                reasons.append("contains_original_identity_tokens")
            if len(same_rel) >= 5:
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
                "exact_source_matches": exact[:12],
                "same_relative_paths_count": len(same_rel),
                "same_relative_paths_sample": same_rel[:12],
                "uncommon_name_matches_sample": uncommon_name_matches[:12],
                "line_overlap": overlaps,
                "identity_hits": ids[:12],
                "suspicious_dirs": sdirs,
            })

    main_results = [r for r in results if r["main_agent"]]
    print(json.dumps({
        "total_flagged_detected": len(results),
        "main_flagged_detected": len(main_results),
        "by_evidence": dict(collections.Counter(r["evidence"] for r in results)),
        "main_by_evidence": dict(collections.Counter(r["evidence"] for r in main_results)),
        "main_by_agent": dict(collections.Counter(r["agent"] for r in main_results)),
        "main_by_kind": dict(collections.Counter("orig_language" if r["wrote"] == r["orig"] else "other_wrong_language" for r in main_results)),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
