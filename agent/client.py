"""Headless coding-agent invocation (the 'model half' of the pipeline).

The pipeline is agent-agnostic: it asks the agent to read the repo and WRITE its
artifact file, then schema-validates that file. So ANY capable headless coding agent
plugs in behind run_headless(). Two engines are wired:

  claude -> `claude -p ...`        (Claude Code)
  codex  -> `codex exec ...`       (OpenAI Codex CLI)

The agent runs on the HOST (not in the per-test hermetic container). Exact CLI flags
evolve - confirm with `claude --help` / `codex --help`. We do NOT depend on either
engine's stdout format: the contract is the written artifact file, which is engine-
neutral.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

# All pipeline codex calls run at this reasoning effort. codex tiers: low < medium < high < xhigh
# (gpt-5.5 default is medium). Set to "medium" for SPEED: high/xhigh were ~2-3x slower per stage; the
# stage6 review->repair loop + gates clean up quality, so medium generation is an acceptable trade.
# Bump to "high"/"xhigh" for single-repo max quality. Override per call via run_headless(..., reasoning_effort=...).
CODEX_REASONING_EFFORT = "medium"

# 出题 default agent is now Claude Code (Opus 4.8) at medium effort (user upgraded to 20x Claude quota).
# "opus" is the alias for the latest Opus (= 4.8). Override per-deployment via env without code change.
CLAUDE_MODEL = os.environ.get("BENCH_CLAUDE_MODEL", "opus")
CLAUDE_EFFORT = os.environ.get("BENCH_CLAUDE_EFFORT", "medium")
# Settings file that turns OFF Claude Code's cross-session auto-memory (no fact carryover between exams ->
# no data pollution). Written once under the home; passed via --settings on every claude invocation.
CLAUDE_SETTINGS = os.environ.get("BENCH_CLAUDE_SETTINGS", "")


def agent_available(engine: str) -> bool:
    return shutil.which({"claude": "claude", "codex": "codex"}[engine]) is not None


def run_headless(prompt: str, cwd: str, allowed_tools, engine: str = "claude",
                 timeout: int = 1200, model: str | None = None,
                 add_dirs: list[str] | None = None, reasoning_effort: str | None = None) -> dict:
    if not agent_available(engine):
        raise RuntimeError(f"`{engine}` not on PATH; use --agent stub or install it")
    if engine == "claude":
        return _run_claude(prompt, cwd, allowed_tools, timeout, model, add_dirs, reasoning_effort)
    if engine == "codex":
        return _run_codex(prompt, cwd, allowed_tools, timeout, model, add_dirs, reasoning_effort)
    raise ValueError(f"unknown engine {engine}")


def _run_claude(prompt, cwd, allowed_tools, timeout, model, add_dirs, reasoning_effort=None) -> dict:
    # NO --continue/--resume -> every call is a FRESH session (no conversation carryover); --settings
    # points at a config with auto-memory OFF -> no cross-exam fact pollution. --effort pins think depth.
    cmd = ["claude", "-p", prompt,
           "--output-format", "json",
           "--permission-mode", "acceptEdits",          # unattended: auto-accept file writes
           "--effort", reasoning_effort or CLAUDE_EFFORT,
           "--model", model or CLAUDE_MODEL,            # 出题: Opus 4.8 (account default is opus anyway)
           "--allowedTools", ",".join(allowed_tools)]
    if CLAUDE_SETTINGS:
        cmd += ["--settings", CLAUDE_SETTINGS]
    for d in (add_dirs or []):
        cmd += ["--add-dir", d]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"raw": p.stdout, "stderr": p.stderr[-1000:], "returncode": p.returncode}


def _run_codex(prompt, cwd, allowed_tools, timeout, model, add_dirs, reasoning_effort=None) -> dict:
    # codex-cli >=0.141: `codex exec [OPTIONS] [PROMPT]` (prompt is positional).
    # Codex governs tool access via its sandbox, not an --allowedTools list, so
    # `allowed_tools` is advisory. -C/--cd = working root; --add-dir = extra
    # read/write dirs (the repo source); workspace-write lets it write artifacts
    # unattended; --skip-git-repo-check because out/<id> is not a git repo.
    # -c model_reasoning_effort pins reasoning DEPTH (a config override, not a model swap).
    cmd = ["codex", "exec", prompt,
           "--cd", cwd,
           # This cube-studio container is unprivileged: bubblewrap (codex's sandbox backend) cannot
           # init (no user namespaces — same reason there's no docker), so the default --full-auto
           # (workspace-write sandbox) makes EVERY codex file-write fail. We turn codex's own sandbox
           # OFF; the disposable container IS the isolation boundary (node is wiped after the run).
           # USER-AUTHORIZED 2026-06-27.
           "--sandbox", "danger-full-access",   # codex exec is already non-interactive (auto-runs cmds);
                                                # this only removes the broken bwrap FS sandbox.
           "--skip-git-repo-check",
           "--color", "never",
           "-c", f"model_reasoning_effort={reasoning_effort or CODEX_REASONING_EFFORT}"]
    for d in (add_dirs or []):
        cmd += ["--add-dir", d]
    if model:
        cmd += ["-m", model]
    # if a stage needs the agent to run build/SUT commands that escape the sandbox,
    # swap the sandbox flag for --dangerously-bypass-approvals-and-sandbox.
    # stdin=DEVNULL: codex appends any piped stdin to the prompt — make sure none leaks in.
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    return {"engine": "codex", "raw": p.stdout[-2000:], "stderr": p.stderr[-1000:],
            "returncode": p.returncode}
