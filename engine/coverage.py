"""Multi-format coverage collector for the differential-oracle loop.

  go         -> go tool covdata over per-run GOCOVERDIR dirs            [proven]
  lcov       -> *.info (Rust cargo-llvm-cov, C/C++, node c8 --reporter=lcov)
  coveragepy -> coverage.json (run `coverage json` in the container entrypoint)
  none       -> no signal (loop falls back to the per-module equivalence-class quota)

Each black-box run mounts a fresh cover dir; the loop passes the list of dirs here.
Returns {covered:[loc], uncovered:[loc], block_coverage, pct_statements}.
"""
from __future__ import annotations

import glob
import json
import os

import gocover


def wants_cover_dirs(lang: str) -> bool:
    return lang in ("go", "lcov", "coveragepy")


def pct(lang: str, cover_dirs) -> float:
    if lang == "go":
        return gocover.pct_value(cover_dirs)
    return collect(lang, cover_dirs, None).get("pct_statements", 0.0)


def _shape(covered, uncovered):
    covered, uncovered = set(covered), set(uncovered) - set(covered)
    total = len(covered) + len(uncovered)
    return {"covered": sorted(covered), "uncovered": sorted(uncovered),
            "block_coverage": (len(covered) / total) if total else 0.0,
            "pct_statements": round(100 * len(covered) / total, 1) if total else 0.0}


def _from_lcov(cover_dirs):
    covered, uncovered, cur = [], [], None
    for d in cover_dirs:
        for info in glob.glob(os.path.join(d, "**", "*.info"), recursive=True):
            with open(info, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("SF:"):
                        cur = line[3:].strip()
                    elif line.startswith("DA:"):
                        ln, cnt = line[3:].strip().split(",")[:2]
                        (covered if int(cnt) > 0 else uncovered).append(f"{cur}:{ln}")
    return _shape(covered, uncovered)


def _from_coveragepy(cover_dirs):
    covered, uncovered = [], []
    for d in cover_dirs:
        for j in glob.glob(os.path.join(d, "**", "coverage.json"), recursive=True):
            data = json.loads(open(j, encoding="utf-8").read())
            for f, fd in data.get("files", {}).items():
                covered += [f"{f}:{ln}" for ln in fd.get("executed_lines", [])]
                uncovered += [f"{f}:{ln}" for ln in fd.get("missing_lines", [])]
    return _shape(covered, uncovered)


def collect(lang: str, cover_dirs, profile_path) -> dict:
    if lang == "go":
        return gocover.ledger(cover_dirs, profile_path)
    if lang == "lcov":
        return _from_lcov(cover_dirs)
    if lang == "coveragepy":
        return _from_coveragepy(cover_dirs)
    if lang == "none":
        return {"covered": [], "uncovered": [], "block_coverage": 0.0, "pct_statements": 0.0, "mode": "none"}
    raise NotImplementedError(f"coverage mode '{lang}' not supported")
