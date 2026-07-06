"""Stage 0 - ingest & baseline.

Clones git sources, then:
  docker mode -> the AGENT writes Dockerfile.codebench + 00_runtime.json (how to build/run
                 an arbitrary repo); we `docker build` it and run an offline smoke. Build
                 failures drop the repo here (Stage 0 is the real filter). 00_runtime.json
                 (service/pipeline/dependencies) is merged into the config by the orchestrator.
  local  mode -> run baseline tests + build the `-cover` binary (proven on the go/cli path).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "engine"))
import client
import dockermirror


def _clone(source, dest):
    dest = pathlib.Path(dest)
    if dest.exists():
        return True, None
    ref = source.get("ref")
    cmd = ["git", "clone"] + ([] if ref else ["--depth", "1"]) + [source["url"], str(dest)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return False, "git clone failed: " + p.stderr[-300:]
    if ref:
        subprocess.run(["git", "-C", str(dest), "checkout", ref], capture_output=True)
    return True, None


def _agent_containerize(repo_src, out_dir, config, agent_mode):
    """Agent writes Dockerfile.codebench (in repo) + 00_runtime.json (in out_dir)."""
    prompt = (ROOT / "prompts" / "stage0_build.md").read_text(encoding="utf-8") \
        .replace("{scenario_type}", config.get("scenario_type", "cli")) \
        .replace("{language}", str(config.get("language", "unknown"))) \
        .replace("{out_dir}", str(out_dir))
    client.run_headless(prompt, cwd=str(repo_src),
                        allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                        engine=agent_mode, add_dirs=[str(out_dir)], timeout=1800)


def _agent_fix_dockerfile(repo_src, out_dir, config, agent_mode, build_stdout, build_stderr):
    """Feed the docker-build failure back to the agent so it repairs Dockerfile.codebench + rebuilds."""
    err = (build_stdout or "")[-1500:] + "\n--- stderr ---\n" + (build_stderr or "")[-2500:]
    prompt = (ROOT / "prompts" / "stage0_fix.md").read_text(encoding="utf-8") \
        .replace("{scenario_type}", config.get("scenario_type", "cli")) \
        .replace("{language}", str(config.get("language", "unknown"))) \
        .replace("{build_error}", err)
    client.run_headless(prompt, cwd=str(repo_src),
                        allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                        engine=agent_mode, add_dirs=[str(out_dir)], timeout=1800)


def _agent_build_local(repo_src, out_dir, config, agent_mode):
    """LOCAL mode: agent writes build.sh (native build) + 00_runtime.json (launch/smoke/deps)."""
    prompt = (ROOT / "prompts" / "stage0_build_local.md").read_text(encoding="utf-8") \
        .replace("{scenario_type}", config.get("scenario_type", "cli")) \
        .replace("{language}", str(config.get("language", "unknown"))) \
        .replace("{out_dir}", str(out_dir))
    client.run_headless(prompt, cwd=str(repo_src),
                        allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                        engine=agent_mode, add_dirs=[str(out_dir)], timeout=1800)


def _agent_fix_build(repo_src, out_dir, config, agent_mode, out, err):
    """Feed the build.sh failure back to the agent so it repairs build.sh + rebuilds (LOCAL mode)."""
    e = (out or "")[-1500:] + "\n--- stderr ---\n" + (err or "")[-2500:]
    prompt = (ROOT / "prompts" / "stage0_fix_local.md").read_text(encoding="utf-8") \
        .replace("{scenario_type}", config.get("scenario_type", "cli")) \
        .replace("{language}", str(config.get("language", "unknown"))) \
        .replace("{out_dir}", str(out_dir)) \
        .replace("{build_error}", e)
    client.run_headless(prompt, cwd=str(repo_src),
                        allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                        engine=agent_mode, add_dirs=[str(out_dir)], timeout=1800)


def _local_agent_build(repo_src, out_dir, config, agent_mode, info):
    """Have the agent write build.sh, then run it with a repair loop (mirror of the docker build loop)."""
    build_sh = repo_src / "build.sh"
    rtj = out_dir / "00_runtime.json"
    have_launch = False
    if rtj.exists():
        try:
            have_launch = bool(json.loads(rtj.read_text(encoding="utf-8")).get("launch"))
        except Exception:
            pass
    # build.sh 在 repo(可能是旧 run 残留),00_runtime.json 在 out_dir(被清/重置会丢);缺任一都要重出,
    # 否则 build.sh 存在→跳过 agent→launch 永远补不回来。
    if not build_sh.exists() or not have_launch:
        _agent_build_local(repo_src, out_dir, config, agent_mode)
    if not build_sh.exists():
        return False, "agent did not write build.sh (use --agent codex)"
    bt = config.get("local_build_timeout_s", 1800)
    max_attempts = config.get("build_repair_attempts", 3)
    b = None
    for attempt in range(max_attempts):
        try:
            b = subprocess.run(["bash", str(build_sh)], capture_output=True, text=True,
                               cwd=str(repo_src), timeout=bt)
        except subprocess.TimeoutExpired as te:
            so, se = te.stdout or "", te.stderr or ""
            if isinstance(so, bytes): so = so.decode("utf-8", "replace")
            if isinstance(se, bytes): se = se.decode("utf-8", "replace")
            b = subprocess.CompletedProcess([], 124, so, se + f"\n[build.sh exceeded {bt}s timeout - killed]")
        (out_dir / "00_baseline" / "build.log").write_text((b.stdout or "") + (b.stderr or ""), encoding="utf-8")
        if b.returncode == 0:
            info["build_attempts"] = attempt + 1
            return True, None
        if attempt < max_attempts - 1:
            info.setdefault("build_repair_errors", []).append(b.stderr[-300:])
            _agent_fix_build(repo_src, out_dir, config, agent_mode, b.stdout, b.stderr)
    info["build_attempts"] = max_attempts
    info["build_error"] = (b.stderr if b else "")[-1500:]
    return False, "local build.sh failed after %d attempt(s): %s" % (max_attempts, (b.stderr if b else "")[-300:])


def run(repo_id, repo_src, config, out_dir, agent_mode="stub", go="go"):
    out_dir = pathlib.Path(out_dir)
    (out_dir / "00_baseline").mkdir(parents=True, exist_ok=True)
    rt = config.get("runtime") or {"mode": "local"}
    info = {"repo_id": repo_id, "scenario_type": config.get("scenario_type"),
            "language": config.get("language"), "runtime_mode": rt.get("mode"),
            "coverage": config.get("coverage")}

    source = config.get("source")
    if source and source.get("kind") == "git":
        ok, err = _clone(source, repo_src)
        if not ok:
            return False, err
    repo_src = pathlib.Path(repo_src)

    def _save():
        (out_dir / "00_baseline" / "baseline.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    if rt.get("mode") == "docker":
        image = config.get("image")
        df = repo_src / "Dockerfile.codebench"
        # agent writes the per-repo Dockerfile + 00_runtime.json (skip if already there = resume)
        if not df.exists():
            if agent_mode in ("claude", "codex"):
                _agent_containerize(repo_src, out_dir, config, agent_mode)
            elif rt.get("dockerfile"):                       # stub: fall back to a preset template
                df = ROOT / rt["dockerfile"]
        if not df.exists():
            info["error"] = "no Dockerfile.codebench (use --agent codex, or set runtime.dockerfile)"
            _save(); return False, info["error"]
        # Build with an AGENT REPAIR LOOP: build -> on failure feed the error back to the agent to
        # fix Dockerfile.codebench -> rebuild (up to N attempts). Previously: single build, drop on fail.
        agentic = agent_mode in ("claude", "codex") and df.name == "Dockerfile.codebench"
        max_attempts = config.get("build_repair_attempts", 3) if agentic else 1
        b = None
        for attempt in range(max_attempts):
            if df.name == "Dockerfile.codebench":     # Docker Hub blocked here -> rewrite FROMs to mirror
                try:
                    ch = dockermirror.mirrorize_file(df)
                    if ch:
                        info["base_image_mirrored"] = [f"{a} -> {c}" for a, c in ch]
                except Exception as e:
                    info["mirror_warn"] = repr(e)
            bt = config.get("build_timeout_s", 720)               # cap pathological builds (e.g. huge rust)
            try:
                b = subprocess.run(["docker", "build", "-t", image, "-f", str(df), str(repo_src)],
                                   capture_output=True, text=True, timeout=bt)
            except subprocess.TimeoutExpired as te:
                try:                                              # jobs=1 -> the only running container is this build
                    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=15).stdout.split()
                    if ids:
                        subprocess.run(["docker", "kill", *ids], capture_output=True, timeout=30)
                except Exception:
                    pass
                so, se = te.stdout or "", te.stderr or ""
                if isinstance(so, bytes): so = so.decode("utf-8", "replace")
                if isinstance(se, bytes): se = se.decode("utf-8", "replace")
                b = subprocess.CompletedProcess([], 124, so, se + f"\n[docker build exceeded {bt}s timeout - killed]")
            (out_dir / "00_baseline" / "docker_build.log").write_text(
                (b.stdout or "") + (b.stderr or ""), encoding="utf-8")
            if b.returncode == 0:
                info["build_attempts"] = attempt + 1
                break
            if attempt < max_attempts - 1 and agentic:    # repair: hand the error to the agent, retry
                info.setdefault("build_repair_errors", []).append(b.stderr[-300:])
                _agent_fix_dockerfile(repo_src, out_dir, config, agent_mode, b.stdout, b.stderr)
        if b.returncode != 0:
            info["build_attempts"] = max_attempts
            info["docker_build_error"] = b.stderr[-1500:]
            _save(); return False, f"docker build failed after {max_attempts} attempt(s): " + b.stderr[-300:]
        info["image"] = image
        if config.get("scenario_type") == "cli":             # offline self-check
            rtj = out_dir / "00_runtime.json"
            smoke = ["--help"]
            if rtj.exists():
                try:
                    smoke = json.loads(rtj.read_text(encoding="utf-8")).get("smoke") or ["--help"]
                except Exception:
                    pass
            s = subprocess.run(["docker", "run", "--rm", image, *smoke], capture_output=True)
            info["smoke"] = "ran" if s.returncode is not None else "FAIL"
    else:                                                    # LOCAL mode — native build, no docker
        launch = config.get("launch") or ([config.get("binary")] if config.get("binary") else None)
        if agent_mode in ("claude", "codex"):
            # agent writes build.sh + 00_runtime.json(launch); build with a repair loop
            ok, lerr = _local_agent_build(repo_src, out_dir, config, agent_mode, info)
            if not ok:
                _save(); return False, lerr
            rtj = out_dir / "00_runtime.json"
            if rtj.exists():
                try:
                    launch = json.loads(rtj.read_text(encoding="utf-8")).get("launch") or launch
                except Exception:
                    pass
        else:                                                # stub/preset path (proven on go/cli): no agent
            test_cmd = rt.get("test_cmd") or (["go", "test", "./..."] if config.get("coverage") == "go" else None)
            if test_cmd:
                t = subprocess.run(test_cmd, capture_output=True, text=True, cwd=str(repo_src))
                info["baseline_test"] = "pass" if t.returncode == 0 else "FAIL"
                if t.returncode != 0:
                    info["test_output"] = (t.stdout + t.stderr)[-1500:]
                    _save(); return False, "baseline test failed"
        if config.get("coverage") == "go":                   # build the instrumented binary (both paths)
            cover_bin = (launch[0] if launch else None) or str(repo_src / (config.get("binary") or "app"))
            b = subprocess.run(["go", "build", "-cover", "-o", cover_bin, "."],
                               capture_output=True, text=True, cwd=str(repo_src))
            if b.returncode != 0:
                return False, "go build -cover failed: " + b.stderr[-500:]
            info["cover_binary"] = cover_bin
            launch = [cover_bin]
        if not launch:
            info["error"] = "no launch command (00_runtime.json missing 'launch')"
            _save(); return False, info["error"]
        info["launch"] = launch
        if agent_mode in ("claude", "codex") and config.get("scenario_type") == "cli":   # native baseline smoke
            smoke = []
            rtj = out_dir / "00_runtime.json"
            if rtj.exists():
                try:
                    smoke = json.loads(rtj.read_text(encoding="utf-8")).get("smoke") or []
                except Exception:
                    smoke = []
            try:
                s = subprocess.run([*launch, *(smoke or ["--help"])], capture_output=True,
                                   cwd=str(repo_src), timeout=60)
                info["smoke"] = "ran" if s.returncode is not None else "FAIL"
            except Exception as e:
                info["smoke"] = "error: " + repr(e)[:200]

    _save()
    return True, None
