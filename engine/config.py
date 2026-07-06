"""Dataset manifest -> normalized per-repo config (language presets + overrides).

The framework hardcodes NO repo logic. Per-repo specifics come from the manifest;
omitted fields fall back to a language preset. The result is a plain dict consumed
by stage0/stage5/orchestrate (back-compatible with the hand-written configs/*.json).
"""
from __future__ import annotations

import copy
import json
import pathlib

# Defaults a preset supplies when the manifest omits them. Docker is the cross-language
# substrate; cover.mode selects the coverage collector (engine/coverage.py).
PRESETS = {
    "go":     {"dockerfile": "docker/ref.Dockerfile.go-cli",   "test_cmd": ["go", "test", "./..."],
               "cover": {"mode": "go"}},
    "python": {"dockerfile": "docker/ref.Dockerfile.py-cli",
               "cover": {"mode": "coveragepy", "collect": "/cover/coverage.json"}},
    "rust":   {"dockerfile": "docker/ref.Dockerfile.rust-cli",
               "cover": {"mode": "lcov", "collect": "/cover/lcov.info"}},
    "node":   {"dockerfile": "docker/ref.Dockerfile.node-cli",
               "cover": {"mode": "lcov", "collect": "/cover/lcov.info"}},
}


def load_manifest(path) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def normalize(repo: dict, defaults: dict, root) -> dict:
    cfg = copy.deepcopy(repo)
    cfg["repo_id"] = repo["id"]
    preset = PRESETS.get(repo.get("language"), {})

    runtime = {"mode": defaults.get("runtime_mode", "docker")}
    if "dockerfile" in preset:
        runtime["dockerfile"] = preset["dockerfile"]
    if "test_cmd" in preset:
        runtime["test_cmd"] = preset["test_cmd"]
    runtime["cover"] = dict(preset.get("cover", {"mode": "none"}))
    # apply manifest overrides
    over = repo.get("runtime", {})
    cover_over = over.pop("cover", None) if isinstance(over, dict) else None
    runtime.update(over or {})
    if cover_over:
        runtime["cover"].update(cover_over)
    cfg["runtime"] = runtime
    cfg["coverage"] = runtime["cover"]["mode"]          # back-compat key
    cfg["image"] = repo.get("runtime", {}).get("image") or f"ref-{repo['id']}:latest"
    cfg["quota"] = repo.get("quota", defaults.get("quota", 20))

    src = repo["source"]
    cfg["src"] = src["path"] if src["kind"] == "path" else str(pathlib.Path(root) / "repos" / repo["id"])
    cfg["out_dir"] = str(pathlib.Path(root) / "out" / repo["id"])
    return cfg


def repo_configs(manifest: dict, root) -> list[dict]:
    defaults = manifest.get("defaults", {})
    return [normalize(r, defaults, root) for r in manifest["repos"]]


def load_repo(repo_id: str, manifest_path, root) -> dict:
    man = load_manifest(manifest_path)
    for r in man["repos"]:
        if r["id"] == repo_id:
            return normalize(r, man.get("defaults", {}), root)
    raise KeyError(f"repo {repo_id} not in manifest")
