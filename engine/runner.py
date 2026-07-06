"""Execution backends for the system-under-test (CLI scenario).

The whole benchmark drives the SUT only at the process boundary. A Runner takes an
Invocation (argv + exact stdin bytes + input files) and returns an Observation
(exit code + exact stdout/stderr bytes + produced files). The SAME Runner interface
is used to (a) capture golden from the original (ref) and (b) grade a candidate (cand).

LocalRunner  - native subprocess, byte-exact stdin/stdout, per-run GOCOVERDIR.
               Used for the gron pilot (host has Go 1.24, no Docker daemon).
DockerRunner - runs the SUT in a one-shot container WITH network available (the production path);
               determinism is enforced by the stage5 double-run check, NOT by --network none.

Byte-exactness matters: PowerShell pipes inject a UTF-8 BOM and rewrite line endings,
which made gron reject its own testdata. subprocess with input=<bytes> avoids that.
"""
from __future__ import annotations

import dataclasses
import os
import pathlib
import shutil
import subprocess
import tempfile
import uuid


@dataclasses.dataclass
class Invocation:
    argv: list[str]                                   # args AFTER the binary, e.g. ["-m", "-u"]
    stdin: bytes = b""                                # exact bytes fed to stdin
    files: dict[str, bytes] = dataclasses.field(default_factory=dict)  # input files placed in workdir
    timeout_s: float = 30.0


@dataclasses.dataclass
class Observation:
    exit_code: int
    stdout: bytes
    stderr: bytes
    out_files: dict[str, bytes]                       # files created/changed in the workdir
    cover_dir: str | None = None                      # dir holding this run's coverage
    timed_out: bool = False
    extra: dict = dataclasses.field(default_factory=dict)  # structured outputs (service http steps, ...)


class Runner:
    def run(self, inv: Invocation) -> Observation:    # pragma: no cover - interface
        raise NotImplementedError


def _hermetic_env(extra: dict | None) -> dict:
    """Deterministic env for the pilot. True isolation is the DockerRunner's job;
    here we inherit the host env (so the Windows exe finds SYSTEMROOT/TEMP) and pin
    the determinism-sensitive bits."""
    env = dict(os.environ)
    env.update({"TZ": "UTC", "LC_ALL": "C", "LANG": "C", "NO_COLOR": "1"})
    if extra:
        env.update(extra)
    return env


def _snapshot(root: str) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    base = pathlib.Path(root)
    for p in base.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(base)).replace("\\", "/")
            out[rel] = p.read_bytes()
    return out


def _docker_user_args() -> list:
    """Run the container as the host user so any file the SUT writes into the
    bind-mounted workdir is host-owned (not root). Without this, a SUT that emits
    output files (e.g. an export) creates root-owned files the non-root host can't
    read back -> PermissionError when snapshotting outputs. HOME=/tmp keeps tools
    that need a writable home happy when the uid isn't in the image's passwd."""
    if hasattr(os, "getuid"):
        return ["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    return []


class LocalRunner(Runner):
    def __init__(self, binary: str, cover_root: str | None = None, env: dict | None = None):
        self.binary = binary
        self.cover_root = cover_root          # set when `binary` is built with `go build -cover`
        self.base_env = env or {}

    def run(self, inv: Invocation) -> Observation:
        workdir = tempfile.mkdtemp(prefix="codebench_run_")
        try:
            for name, data in inv.files.items():
                fp = pathlib.Path(workdir, name)
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(data)
            before = _snapshot(workdir)

            env = _hermetic_env(self.base_env)
            cover_dir = None
            if self.cover_root:
                cover_dir = os.path.join(self.cover_root, uuid.uuid4().hex)
                os.makedirs(cover_dir, exist_ok=True)
                env["GOCOVERDIR"] = cover_dir

            timed_out = False
            try:
                proc = subprocess.run(
                    [self.binary, *inv.argv],
                    input=inv.stdin,
                    capture_output=True,          # bytes in, bytes out (no text decoding)
                    cwd=workdir,
                    env=env,
                    timeout=inv.timeout_s,
                )
                code, out, err = proc.returncode, proc.stdout, proc.stderr
            except subprocess.TimeoutExpired as e:
                timed_out = True
                code = 124
                out = e.stdout or b""
                err = e.stderr or b""

            after = _snapshot(workdir)
            out_files = {k: v for k, v in after.items() if before.get(k) != v}
            return Observation(code, out, err, out_files, cover_dir, timed_out)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


class DockerRunner(Runner):
    """Production backend: one container per invocation, run WITH network (determinism
    is enforced by the double-run check in stage5_loop, not by --network none).

    Runs as the host uid (see _docker_user_args) so files the SUT writes into the
    bind-mounted workdir stay host-owned and readable. For Go coverage the image is
    built with `go build -cover` and GOCOVERDIR is bind-mounted out.
    """
    def __init__(self, image: str, cover_root: str | None = None,
                 cpus: str = "1", memory: str = "512m", docker: str = "docker"):
        self.image = image
        self.cover_root = cover_root
        self.cpus = cpus
        self.memory = memory
        self.docker = docker

    def run(self, inv: Invocation) -> Observation:
        workdir = tempfile.mkdtemp(prefix="codebench_run_")
        cover_dir = None
        try:
            for name, data in inv.files.items():
                fp = pathlib.Path(workdir, name)
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(data)
            before = _snapshot(workdir)

            cmd = [self.docker, "run", "--rm",        # exam-gen + grading run WITH network
                   "--cpus", self.cpus, "--memory", self.memory,
                   *_docker_user_args(),              # host-owned outputs (see BUG: root-owned files)
                   "-e", "TZ=UTC", "-e", "NO_COLOR=1",
                   "-v", f"{workdir}:/work", "-w", "/work"]
            if self.cover_root:
                cover_dir = os.path.join(self.cover_root, uuid.uuid4().hex)
                os.makedirs(cover_dir, exist_ok=True)
                cmd += ["-e", "GOCOVERDIR=/cover", "-v", f"{cover_dir}:/cover"]
            cmd += [self.image, *inv.argv]

            timed_out = False
            try:
                proc = subprocess.run(cmd, input=inv.stdin, capture_output=True,
                                      timeout=inv.timeout_s + 10)
                code, out, err = proc.returncode, proc.stdout, proc.stderr
            except subprocess.TimeoutExpired as e:
                timed_out = True
                code, out, err = 124, e.stdout or b"", e.stderr or b""

            after = _snapshot(workdir)
            out_files = {k: v for k, v in after.items() if before.get(k) != v}
            return Observation(code, out, err, out_files, cover_dir, timed_out)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
