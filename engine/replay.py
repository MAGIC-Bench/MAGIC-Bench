"""Scenario backends. backend.run(runner, prefix, testinput, config) -> Observation.
The same backend captures golden from the original and grades a candidate.

testinput shapes (produced by the agent in Stage 5):
  cli:      {argv, stdin|stdin_b64, files}             -> exit/stdout/stderr/out_files
  service:  {steps:[{method,path,headers?,body?,bind?}]} -> Observation.extra["http"]=[{status,headers,body}]
  pipeline: {files:{...input dataset...}}               -> Observation.out_files = produced /out files

cli is implemented + proven. service/pipeline are real but need a Docker daemon
(one --network none container per test); not exercised in this environment.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from runner import Invocation, Observation, _docker_user_args


def _stdin_bytes(inp: dict) -> bytes:
    if inp.get("stdin_b64"):
        return base64.b64decode(inp["stdin_b64"])
    if inp.get("stdin") is not None:
        return inp["stdin"].encode("utf-8")
    return b""


def _file_bytes(v) -> bytes:
    if isinstance(v, str):
        return base64.b64decode(v)
    if "b64" in v:
        return base64.b64decode(v["b64"])
    return v.get("text", "").encode("utf-8")


def _subst(s: str, binds: dict) -> str:
    return re.sub(r"\$\{(\w+)\}", lambda m: str(binds.get(m.group(1), m.group(0))), s)


def _json_path(body: bytes, expr: str):
    try:
        obj = json.loads(body)
    except Exception:
        return None
    for part in expr.lstrip("$.").split("."):
        if part == "":
            continue
        if isinstance(obj, list):
            obj = obj[int(part)]
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


class CliBackend:
    scenario = "cli"

    def run(self, runner, prefix, testinput, config=None):
        inv = Invocation(
            argv=list(prefix) + testinput.get("argv", []),
            stdin=_stdin_bytes(testinput),
            files={k: _file_bytes(v) for k, v in testinput.get("files", {}).items()},
            timeout_s=testinput.get("timeout_s", 30.0))
        return runner.run(inv)

    def teardown(self):
        pass


class ServiceBackend:
    """One session per repo: DB/cache sidecars (engine/deps.py) + SUT on a shared docker
    network, started once; deps.reset() wipes state BEFORE every test case so no test
    pollutes the next; torn down at the end. Needs a Docker daemon (not exercised here).
    Service coverage flushes when the SUT container stops (teardown) -> collected at
    end-of-session (the loop falls back to module-quota during rounds)."""
    scenario = "service"

    def __init__(self):
        self._session = None

    def _ensure(self, runner, config):
        if self._session:
            return self._session
        import deps as deps_mod
        net = f"codebench-{config.get('repo_id', 'repo')}-{uuid.uuid4().hex[:8]}"
        d = deps_mod.Deps(config.get("dependencies", []), net)
        dep_env = d.start()                                  # DB/cache sidecars up
        svc = config.get("service", {})
        port = svc.get("port", 8080)
        cover_root = getattr(runner, "cover_root", None)
        cover_dir = None
        cmd = ["docker", "run", "-d", "--rm", "--name", f"{net}-sut", "--network", net,
               "-e", "TZ=UTC", "-e", "NO_COLOR=1"]
        for k, v in {**dep_env, **(svc.get("env") or {})}.items():
            cmd += ["-e", f"{k}={v}"]
        if cover_root:
            cover_dir = os.path.join(cover_root, uuid.uuid4().hex)
            os.makedirs(cover_dir, exist_ok=True)
            cmd += ["-e", "GOCOVERDIR=/cover", "-v", f"{cover_dir}:/cover"]
        cmd += ["-p", f"0:{port}", config["image"]]
        cid = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        base = self._base_url(cid, port)
        self._wait_health(base + svc.get("health", "/health"), svc.get("start_timeout_s", 30))
        self._session = {"deps": d, "cid": cid, "base": base + svc.get("base_path", ""),
                         "cover_dir": cover_dir}
        return self._session

    def run(self, runner, prefix, testinput, config):
        s = self._ensure(runner, config)
        s["deps"].reset()                                    # ★ per-test state reset (no pollution)
        steps, binds = [], {}
        for st in testinput.get("steps", []):
            resp = self._do(s["base"], st, binds)
            steps.append(resp)
            for name, expr in (st.get("bind") or {}).items():
                binds[name] = _json_path(resp["body_b"], expr)
        for x in steps:
            x["body"] = x.pop("body_b").decode("utf-8", "replace")
        return Observation(0, b"", b"", {}, s["cover_dir"], False, {"http": steps})

    def teardown(self):
        if self._session:
            subprocess.run(["docker", "stop", self._session["cid"]], capture_output=True)
            self._session["deps"].stop()
            self._session = None

    def _base_url(self, cid, port):
        out = subprocess.run(["docker", "port", cid, str(port)], capture_output=True, text=True).stdout
        hostport = out.strip().splitlines()[0].split(":")[-1] if out.strip() else str(port)
        return f"http://127.0.0.1:{hostport}"

    def _wait_health(self, url, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=2)
                return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError(f"service health {url} not ready in {timeout}s")

    def _do(self, base, st, binds):
        url = base + _subst(st["path"], binds)
        data = None
        headers = {k: _subst(v, binds) for k, v in (st.get("headers") or {}).items()}
        if st.get("body") is not None:
            data = json.dumps(st["body"]).encode()
            headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, method=st.get("method", "GET"), headers=headers)
        try:
            r = urllib.request.urlopen(req, timeout=st.get("timeout_s", 15))
            status, body, hdrs = r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            status, body, hdrs = e.code, e.read(), dict(e.headers)
        return {"status": status, "headers": hdrs, "body_b": body}


class LocalServiceBackend(ServiceBackend):
    """No-docker service backend: run the service as a LOCAL process listening on $PORT, with
    engine/deps.py:LocalDeps providing DB/cache via injected env. Reuses ServiceBackend's HTTP
    replay + per-test deps.reset(); only the start (docker run -> local process) and teardown differ.
    Used for BOTH golden capture (original) and grading (candidate) in local mode."""
    scenario = "service"

    def _ensure(self, runner, config):
        if self._session:
            return self._session
        import deps as deps_mod
        d = deps_mod.LocalDeps(config.get("dependencies", []))
        dep_env = d.start()                                   # local DB/cache up, conn URLs in dep_env
        svc = config.get("service", {})
        port = deps_mod._free_port(int(svc.get("port", 8080)))
        launch = config.get("launch") or ([config.get("binary")] if config.get("binary") else None)
        if not launch:
            d.stop()
            raise RuntimeError("LocalServiceBackend: no launch command (00_runtime.json missing 'launch')")
        env = {**os.environ, "PORT": str(port), "TZ": "UTC", "NO_COLOR": "1",
               **dep_env, **(svc.get("env") or {})}           # candidate reads the DB conn from dep_env
        proc = subprocess.Popen(launch, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}"
        try:
            self._wait_health(base + svc.get("health", "/health"), svc.get("start_timeout_s", 30))
        except Exception:
            proc.terminate()
            d.stop()
            raise
        self._session = {"deps": d, "proc": proc, "base": base + svc.get("base_path", ""), "cover_dir": None}
        return self._session

    def teardown(self):
        if self._session:
            p = self._session.get("proc")
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except Exception:
                    p.kill()
            self._session["deps"].stop()
            self._session = None


class PipelineBackend:
    scenario = "pipeline"

    def run(self, runner, prefix, testinput, config):
        pl = config.get("pipeline", {})
        image = config.get("image")
        cover_root = getattr(runner, "cover_root", None)
        work = tempfile.mkdtemp(prefix="codebench_pl_")
        ind, outd = os.path.join(work, "in"), os.path.join(work, "out")
        os.makedirs(ind); os.makedirs(outd)
        try:
            for name, v in testinput.get("files", {}).items():
                p = pathlib.Path(ind, name)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(_file_bytes(v))
            cover_dir = None
            cmd = ["docker", "run", "--rm",          # run WITH network (determinism via double-run)
                   *_docker_user_args(),             # host-owned /out files (else root-owned, unreadable)
                   "-v", f"{ind}:{pl.get('in', '/in')}:ro", "-v", f"{outd}:{pl.get('out', '/out')}",
                   "-e", "TZ=UTC"]
            if cover_root:
                cover_dir = os.path.join(cover_root, uuid.uuid4().hex)
                os.makedirs(cover_dir, exist_ok=True)
                cmd += ["-e", "GOCOVERDIR=/cover", "-v", f"{cover_dir}:/cover"]
            cmd += [image] + pl.get("cmd", [])
            p = subprocess.run(cmd, capture_output=True, timeout=testinput.get("timeout_s", 120))
            out_files = {}
            for fp in pathlib.Path(outd).rglob("*"):
                if fp.is_file():
                    out_files[str(fp.relative_to(outd)).replace("\\", "/")] = fp.read_bytes()
            return Observation(p.returncode, p.stdout, p.stderr, out_files, cover_dir)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def teardown(self):
        pass


_BACKENDS = {"cli": CliBackend, "service": ServiceBackend, "pipeline": PipelineBackend}


def make_backend(scenario_type, config=None, runner=None, prefix=None):
    """service: docker -> ServiceBackend(sidecars); else LocalServiceBackend(local process+LocalDeps)."""
    if scenario_type == "service":
        mode = ((config or {}).get("runtime") or {}).get("mode", "local")
        return ServiceBackend() if mode == "docker" else LocalServiceBackend()
    return _BACKENDS[scenario_type]()


def get_backend(scenario_type, config=None):
    return make_backend(scenario_type, config)
