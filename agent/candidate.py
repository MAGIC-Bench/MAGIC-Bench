"""B段 - drive a candidate agent (the system under evaluation) to generate a project from the
EXAM PACKAGE, then build it into a cand-image ready for grading (C段, grade.py).

The candidate sees ONLY the canonical exam package (07_exam/candidate/, built by Stage 8): the
de-identified project brief + API manual + feature list + user stories + NFRs + scrubbed contract +
required language. It NEVER sees the hidden tests/golden. There is ONE package definition (Stage 8);
this module just copies it into the candidate's working SPEC/ dir — no second, divergent spec.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for _d in ("agent", "engine", "stages"):
    sys.path.insert(0, str(ROOT / _d))
import client
import dockermirror
import stage8_package


def assemble_spec(repo_out, spec_dir, config=None):
    """Copy the canonical candidate package (07_exam/candidate/) into spec_dir, building it via
    Stage 8 first if it isn't there yet. This is the SAME de-identified package an external
    candidate receives — there is no second spec definition to drift from."""
    repo_out, spec_dir = pathlib.Path(repo_out), pathlib.Path(spec_dir)
    cand_src = repo_out / "07_exam" / "candidate"
    if not (cand_src.exists() and any(cand_src.iterdir())):
        stage8_package.run(repo_out, config or {"scenario_type": "cli"})
    spec_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for p in sorted(cand_src.iterdir()):
        if p.is_file():
            (spec_dir / p.name).write_bytes(p.read_bytes())
            copied.append(p.name)
    return copied


def generate(repo_out, scenario_type, candidate_dir, engine="codex", model=None, timeout=2400, config=None):
    candidate_dir = pathlib.Path(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    cfg = dict(config or {})
    cfg.setdefault("scenario_type", scenario_type)
    copied = assemble_spec(repo_out, candidate_dir / "SPEC", cfg)
    if not copied:
        raise RuntimeError(f"no candidate package in {repo_out}/07_exam/candidate (run Stages 1-8 first)")
    prompt = (ROOT / "prompts" / "candidate.md").read_text(encoding="utf-8") \
        .replace("{scenario_type}", scenario_type)
    # the candidate agent writes its project into candidate_dir (its working root)
    client.run_headless(prompt, cwd=str(candidate_dir), allowed_tools=["Read", "Write", "Bash"],
                        engine=engine, model=model, timeout=timeout)
    return candidate_dir


def build_image(candidate_dir, image_tag, docker="docker"):
    cd = pathlib.Path(candidate_dir)
    if not (cd / "Dockerfile").exists():
        return False, "candidate produced no Dockerfile"
    try:
        dockermirror.mirrorize_file(cd / "Dockerfile")   # Docker Hub GFW-blocked -> China mirror
    except Exception:
        pass
    p = subprocess.run([docker, "build", "-t", image_tag, str(cd)], capture_output=True, text=True)
    return (p.returncode == 0), (None if p.returncode == 0 else p.stderr[-1000:])
