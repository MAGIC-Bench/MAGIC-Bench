"""Pick the right execution substrate per repo: Local vs Docker runner, and the
cli/service/pipeline backend. Keeps the cli+local path (gron) working as a special
case while enabling cross-language Docker + service/pipeline for the dataset.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
from runner import LocalRunner, DockerRunner
import replay as replay_mod


def make_runner(config, cover_root=None):
    rt = config.get("runtime") or {"mode": "local"}
    if rt.get("mode") == "docker":
        return DockerRunner(image=config.get("image") or f"ref-{config['repo_id']}:latest",
                            cover_root=cover_root)
    launch = config.get("launch") or [config.get("binary")]
    return LocalRunner(launch[0], cover_root=cover_root)


def launch_prefix(config):
    rt = config.get("runtime") or {"mode": "local"}
    if rt.get("mode") == "docker":
        return []                      # the image entrypoint IS the binary
    launch = config.get("launch") or [config.get("binary")]
    return list(launch[1:])


def make_backend(config, cover_root=None):
    runner = make_runner(config, cover_root)
    prefix = launch_prefix(config)
    return replay_mod.make_backend(config["scenario_type"], config, runner, prefix)
