"""Emit the black-box test suite as a standalone PYTEST grader (做题侧).

Turns out/<id>/05_tests/*.json into a self-contained pytest project the candidate is
graded with. The candidate is plugged in via env (CANDIDATE_BIN for a local binary, or
CANDIDATE_IMAGE for a docker image). Per-module pass-rate is printed at the end.

  CANDIDATE_BIN=./my_impl   pytest 07_exam/grader -q
  CANDIDATE_IMAGE=cand:tag  pytest 07_exam/grader -q

All three scenarios are graded: the emitted conftest carries CliSUT / ServiceSUT /
PipelineSUT and picks one by `_grader_meta.json` (written at emit time). Service grading
reuses the deps lifecycle (deps.py is copied into the grader).
"""
from __future__ import annotations

import json
import pathlib
import shutil

ENGINE = pathlib.Path(__file__).resolve().parent

# ---- emitted: _assert.py (standalone, mirrors engine/classify.check) --------
_ASSERT = r'''import base64, json, re

def _text(v):
    return bytes(v).decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else str(v)

def _extract(obs, field):
    if field == "exit": return obs["exit"]
    if field == "stdout": return obs["stdout"]
    if field == "stderr": return obs["stderr"]
    if field.startswith("file:"): return obs.get("files", {}).get(field[5:])
    if field.startswith("http:"):
        parts = field.split(":", 3); step = obs["http"][int(parts[1])]; what = parts[2]
        return {"status": step["status"], "body": step["body"]}.get(what) if what != "header" \
            else step.get("headers", {}).get(parts[3])
    raise KeyError(field)

def _enc(v):
    if isinstance(v, bool): return {"bool": v}
    if isinstance(v, int): return {"int": v}
    if v is None: return {"null": True}
    b = bytes(v) if isinstance(v, (bytes, bytearray)) else str(v).encode()
    try:
        t = b.decode("utf-8")
        if t.encode() == b: return {"utf8": t}
    except Exception: pass
    return {"b64": base64.b64encode(b).decode()}

def _norm(rule, v):
    t = _text(v)
    if rule == "crlf_lf": return t.replace("\r\n", "\n")
    if rule == "strip": return t.strip()
    if rule == "rstrip_eol": return "\n".join(l.rstrip() for l in t.replace("\r\n", "\n").split("\n")).strip("\n")
    if rule == "lines_sorted": return "\n".join(sorted(t.replace("\r\n", "\n").rstrip("\n").split("\n")))
    if rule == "json_canonical": return json.dumps(json.loads(t), sort_keys=True, separators=(",", ":"))
    if rule.startswith("regex_extract:"):
        m = re.search(rule[len("regex_extract:"):], t, re.S); return m.group(0) if m else None
    raise ValueError("bad normalize rule: " + rule)

def _inv(rule, v):
    t = _text(v)
    if rule == "nonempty": return len(t) > 0
    if rule == "empty": return len(t) == 0
    if rule == "valid_json":
        try: json.loads(t); return True
        except Exception: return False
    if rule.startswith("regex:"): return re.search(rule[len("regex:"):], t, re.S) is not None
    if rule.startswith("eq_int:"):
        try: return int(v) == int(rule[len("eq_int:"):])
        except Exception: return False
    raise ValueError("bad invariant rule: " + rule)

def assert_all(obs, assertions):
    for a in assertions:
        f, cls = a["field"], a["class"]
        val = _extract(obs, f)
        if cls == "exact":
            assert _enc(val) == a["value"], f"{f}: exact mismatch"
        elif cls == "normalized":
            assert _norm(a["rule"], val) == a["value"], f"{f}: normalized({a['rule']}) mismatch"
        elif cls == "invariant":
            assert _inv(a["rule"], val), f"{f}: invariant({a['rule']}) failed"
        elif cls == "ignored":
            pass
        else:
            raise AssertionError("unknown class: " + cls)
'''

# ---- emitted: conftest.py (SUT fixtures per scenario + per-module reporting) -
_CONFTEST = r'''import base64, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, uuid, collections
import urllib.error, urllib.request
import pytest

sys.path.insert(0, os.path.dirname(__file__))   # so `import deps` (copied in for service) resolves


def _stdin(inp):
    if inp.get("stdin_b64"): return base64.b64decode(inp["stdin_b64"])
    return (inp.get("stdin") or "").encode("utf-8")

def _file(v):
    if isinstance(v, str): return base64.b64decode(v)
    return base64.b64decode(v["b64"]) if "b64" in v else v.get("text", "").encode("utf-8")

def _subst(s, binds):
    return re.sub(r"\$\{(\w+)\}", lambda m: str(binds.get(m.group(1), m.group(0))), s)

def _json_path(body, expr):
    try: obj = json.loads(body)
    except Exception: return None
    for part in expr.lstrip("$.").split("."):
        if part == "": continue
        if isinstance(obj, list): obj = obj[int(part)]
        elif isinstance(obj, dict): obj = obj.get(part)
        else: return None
    return obj

def _meta():
    p = pathlib.Path(__file__).parent / "_grader_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"scenario_type": "cli"}

def _user_args():
    return (["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
            if hasattr(os, "getuid") else [])


class CliSUT:
    """Run the candidate cli: CANDIDATE_BIN (local) or CANDIDATE_IMAGE (docker)."""
    def __init__(self, meta=None):
        self.bin = os.environ.get("CANDIDATE_BIN")
        self.image = os.environ.get("CANDIDATE_IMAGE")
        if not (self.bin or self.image):
            pytest.exit("set CANDIDATE_BIN=<binary> or CANDIDATE_IMAGE=<docker image>")
    def run(self, inp):
        argv = inp.get("argv", [])
        files = {k: _file(v) for k, v in inp.get("files", {}).items()}
        work = tempfile.mkdtemp(prefix="grade_")
        try:
            before = {}
            for n, d in files.items():
                p = pathlib.Path(work, n); p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(d); before[n] = d
            if self.bin:
                cmd = [self.bin, *argv]
            else:
                cmd = ["docker", "run", "--rm", "-i", *_user_args(),
                       "-v", f"{work}:/w", "-w", "/w", "-e", "TZ=UTC", "-e", "NO_COLOR=1", self.image, *argv]
            env = dict(os.environ, TZ="UTC", LC_ALL="C", NO_COLOR="1")
            p = subprocess.run(cmd, input=_stdin(inp), capture_output=True, cwd=work, env=env, timeout=60)
            out_files = {}
            for fp in pathlib.Path(work).rglob("*"):
                if fp.is_file():
                    rel = str(fp.relative_to(work)).replace("\\", "/")
                    data = fp.read_bytes()
                    if before.get(rel) != data:
                        out_files[rel] = data
            return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "files": out_files}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    def teardown(self):
        pass


class ServiceSUT:
    """Start the candidate image once (on a docker network with DB/cache deps), reset dep state
    BEFORE each test, replay the request steps. Mirrors engine/replay.ServiceBackend."""
    def __init__(self, meta):
        self.image = os.environ.get("CANDIDATE_IMAGE")
        if not self.image:
            pytest.exit("service grading needs CANDIDATE_IMAGE=<docker image>")
        self.svc = meta.get("service") or {}
        self.deps_specs = meta.get("dependencies") or []
        self._s = None
    def _ensure(self):
        if self._s: return self._s
        import deps as deps_mod
        net = "cbgrade-" + uuid.uuid4().hex[:8]
        d = deps_mod.Deps(self.deps_specs, net)
        dep_env = d.start()
        port = self.svc.get("port", 8080)
        cmd = ["docker", "run", "-d", "--rm", "--name", net + "-sut", "--network", net,
               "-e", "TZ=UTC", "-e", "NO_COLOR=1", "-e", f"PORT={port}"]
        for k, v in {**dep_env, **(self.svc.get("env") or {})}.items():
            cmd += ["-e", f"{k}={v}"]
        cmd += ["-p", f"0:{port}", self.image]
        cid = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        base = self._base(cid, port)
        self._wait(base + self.svc.get("health", "/health"), self.svc.get("start_timeout_s", 30))
        self._s = {"deps": d, "cid": cid, "base": base + self.svc.get("base_path", "")}
        return self._s
    def run(self, inp):
        s = self._ensure()
        s["deps"].reset()
        steps, binds = [], {}
        for st in inp.get("steps", []):
            resp = self._do(s["base"], st, binds)
            steps.append(resp)
            for name, expr in (st.get("bind") or {}).items():
                binds[name] = _json_path(resp["body_b"], expr)
        for x in steps:
            x["body"] = x.pop("body_b").decode("utf-8", "replace")
        return {"exit": 0, "stdout": b"", "stderr": b"", "files": {}, "http": steps}
    def teardown(self):
        if self._s:
            subprocess.run(["docker", "stop", self._s["cid"]], capture_output=True)
            self._s["deps"].stop()
            self._s = None
    def _base(self, cid, port):
        out = subprocess.run(["docker", "port", cid, str(port)], capture_output=True, text=True).stdout
        hp = out.strip().splitlines()[0].split(":")[-1] if out.strip() else str(port)
        return f"http://127.0.0.1:{hp}"
    def _wait(self, url, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=2); return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError(f"service health {url} not ready in {timeout}s")
    def _do(self, base, st, binds):
        url = base + _subst(st["path"], binds)
        data = None
        headers = {k: _subst(v, binds) for k, v in (st.get("headers") or {}).items()}
        if st.get("body") is not None:
            data = json.dumps(st["body"]).encode(); headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, method=st.get("method", "GET"), headers=headers)
        try:
            r = urllib.request.urlopen(req, timeout=st.get("timeout_s", 15))
            return {"status": r.status, "headers": dict(r.headers), "body_b": r.read()}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "headers": dict(e.headers), "body_b": e.read()}


class PipelineSUT:
    """Run the candidate image with input-path -> output-path binds. Mirrors replay.PipelineBackend."""
    def __init__(self, meta):
        self.image = os.environ.get("CANDIDATE_IMAGE")
        if not self.image:
            pytest.exit("pipeline grading needs CANDIDATE_IMAGE=<docker image>")
        self.pl = meta.get("pipeline") or {}
    def run(self, inp):
        pl = self.pl
        work = tempfile.mkdtemp(prefix="grade_pl_")
        ind, outd = os.path.join(work, "in"), os.path.join(work, "out")
        os.makedirs(ind); os.makedirs(outd)
        try:
            for name, v in inp.get("files", {}).items():
                p = pathlib.Path(ind, name); p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(_file(v))
            cmd = ["docker", "run", "--rm", *_user_args(),
                   "-v", f"{ind}:{pl.get('in', '/in')}:ro", "-v", f"{outd}:{pl.get('out', '/out')}",
                   "-e", "TZ=UTC", self.image] + pl.get("cmd", [])
            p = subprocess.run(cmd, capture_output=True, timeout=inp.get("timeout_s", 120))
            out_files = {}
            for fp in pathlib.Path(outd).rglob("*"):
                if fp.is_file():
                    out_files[str(fp.relative_to(outd)).replace("\\", "/")] = fp.read_bytes()
            return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "files": out_files}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    def teardown(self):
        pass


_SUTS = {"cli": CliSUT, "service": ServiceSUT, "pipeline": PipelineSUT}

@pytest.fixture(scope="session")
def sut():
    meta = _meta()
    inst = _SUTS.get(meta.get("scenario_type", "cli"), CliSUT)(meta)
    try:
        yield inst
    finally:
        inst.teardown()

def pytest_configure(config):
    config.addinivalue_line("markers", "module(name): functional module tag")

_MOD = collections.defaultdict(lambda: [0, 0])   # module -> [passed, total]
_SEC = collections.defaultdict(lambda: [0, 0])   # security metric_id -> [passed, total] (req 2.7)

def pytest_collection_modifyitems(config, items):
    for it in items:
        tc = getattr(it, "callspec", None) and it.callspec.params.get("tc")
        for m in (tc or {}).get("modules", []):
            it.add_marker(pytest.mark.module(m))

def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    for m in getattr(report, "tc_modules", None) or []:
        if m == "SMOKE":                      # smoke is reported on its own, not as a functional module
            continue
        _MOD[m][1] += 1
        if report.passed:
            _MOD[m][0] += 1
    sm = getattr(report, "tc_security", None)
    if sm:
        _SEC[sm][1] += 1
        if report.passed:
            _SEC[sm][0] += 1

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    tc = getattr(item, "callspec", None) and item.callspec.params.get("tc")
    rep.tc_modules = (tc or {}).get("modules", [])
    rep.tc_security = (tc or {}).get("security_metric")

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    tr = terminalreporter
    if _MOD:
        tr.write_sep("=", "per-module pass-rate")
        rates = []
        for m in sorted(_MOD):
            p, t = _MOD[m]
            r = p / t if t else 0.0
            rates.append(r)
            tr.write_line(f"  {m}: {p}/{t}  ({r:.0%})")
        tr.write_line(f"  functional (cross-module mean): {sum(rates)/len(rates):.3f}")
    if _SEC:
        tr.write_sep("=", "security NFR pass-rate (req 2.7)")
        for m in sorted(_SEC):
            p, t = _SEC[m]
            tr.write_line(f"  {m}: {p}/{t}  ({(p/t if t else 0):.0%})")
'''

# ---- emitted: test_blackbox.py (functional + security cases; smoke runs separately) -
_TESTPY = r'''import json, pathlib, pytest
from _assert import assert_all

_CASES = [json.loads(p.read_text(encoding="utf-8"))
          for p in sorted((pathlib.Path(__file__).parent / "cases").glob("*.json"))]
_FUNC = [c for c in _CASES if not c.get("smoke")]   # smoke cases are graded by test_smoke.py

@pytest.mark.parametrize("tc", _FUNC, ids=[c["id"] for c in _FUNC])
def test_blackbox(sut, tc):
    obs = sut.run(tc["input"])
    assert_all(obs, tc["assertions"])
'''

# ---- emitted: test_smoke.py (the must-pass liveness gate; req 2.8) -----------
_SMOKEPY = r'''import json, pathlib, pytest
from _assert import assert_all

_SMOKE = [json.loads(p.read_text(encoding="utf-8"))
          for p in sorted((pathlib.Path(__file__).parent / "cases").glob("*.json"))
          if json.loads(p.read_text(encoding="utf-8")).get("smoke")]

@pytest.mark.skipif(not _SMOKE, reason="no smoke cases packaged")
@pytest.mark.parametrize("tc", _SMOKE, ids=[c["id"] for c in _SMOKE])
def test_smoke(sut, tc):
    obs = sut.run(tc["input"])
    assert_all(obs, tc["assertions"])
'''

_RUN_MD = """# Black-box grader (pytest)

Plug the candidate in via env, then run pytest:

```bash
CANDIDATE_BIN=/path/to/candidate_binary   pytest -q          # local binary (cli)
CANDIDATE_IMAGE=cand-image:tag            pytest -q          # docker image (cli/service/pipeline)
```

Each case in `cases/*.json` becomes one parametrized test. Cases are tagged with their functional
module(s); the run prints a per-module pass-rate + the cross-module functional score. Assertion
classes: exact / normalized / invariant / ignored. The scenario (cli/service/pipeline) is read
from `_grader_meta.json`.

- `pytest test_smoke.py -q`   — the must-pass SMOKE gate (liveness: the build runs and responds).
- `pytest test_blackbox.py -q`— functional + security cases. Security cases carry a `security_metric`
  tag (the NFR metric they evidence); the run prints a security NFR pass-rate section.
"""


def _scrub_case(case, toks):
    """Scrub the original program/repo name out of the GRADED golden. The candidate prints the
    de-identified name ('app') per the scrubbed contract, so judging it against a golden that still
    says the real name -- whether in an `exact`/`normalized` value OR an invariant `regex` rule --
    systematically fails a CORRECT candidate (e.g. golden rule `regex:^jd version` vs candidate
    `app version`). Mirrors stage8's contract scrub; 05_tests stays raw so stage7 can still validate
    against the ORIGINAL (which prints the real name)."""
    import deident
    for a in case.get("assertions", []):
        v = a.get("value")
        if isinstance(v, dict) and isinstance(v.get("utf8"), str):
            v["utf8"] = deident.scrub_text(v["utf8"], toks)
        elif isinstance(v, str):
            a["value"] = deident.scrub_text(v, toks)
        if isinstance(a.get("rule"), str):
            a["rule"] = deident.scrub_text(a["rule"], toks)        # invariant regex/normalized rule
    obs = case.get("observed")
    if isinstance(obs, dict):                                       # preview only (unjudged), keep tidy
        for k, val in list(obs.items()):
            if isinstance(val, str):
                obs[k] = deident.scrub_text(val, toks)
    return case


def _copy_case(tf, dst, scrub_tokens):
    if scrub_tokens:
        c = json.loads(tf.read_text(encoding="utf-8"))
        dst.write_text(json.dumps(_scrub_case(c, scrub_tokens), indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        shutil.copy(tf, dst)


def emit(repo_out, grader_dir, scenario_type="cli", runtime=None, scrub_tokens=None):
    repo_out, grader_dir = pathlib.Path(repo_out), pathlib.Path(grader_dir)
    cases_dir = grader_dir / "cases"
    if grader_dir.exists():
        shutil.rmtree(grader_dir, ignore_errors=True)
    cases_dir.mkdir(parents=True, exist_ok=True)
    n = n_smoke = n_sec = 0
    sec_by_metric = {}
    for tf in sorted((repo_out / "05_tests").glob("*.json")):
        _copy_case(tf, cases_dir / tf.name, scrub_tokens)          # scrub real name out of graded golden
        n += 1
        try:
            c = json.loads(tf.read_text(encoding="utf-8"))
            if c.get("security_metric"):
                n_sec += 1
                sec_by_metric[c["security_metric"]] = sec_by_metric.get(c["security_metric"], 0) + 1
        except Exception:
            pass
    for sf in sorted((repo_out / "05_smoke").glob("*.json")):   # req 2.8: package the smoke suite
        _copy_case(sf, cases_dir / sf.name, scrub_tokens)
        n_smoke += 1
    (grader_dir / "_assert.py").write_text(_ASSERT, encoding="utf-8")
    (grader_dir / "conftest.py").write_text(_CONFTEST, encoding="utf-8")
    (grader_dir / "test_blackbox.py").write_text(_TESTPY, encoding="utf-8")
    (grader_dir / "test_smoke.py").write_text(_SMOKEPY, encoding="utf-8")
    (grader_dir / "RUN.md").write_text(_RUN_MD, encoding="utf-8")
    (grader_dir / "pytest.ini").write_text("[pytest]\naddopts = -ra\n", encoding="utf-8")
    meta = {"scenario_type": scenario_type,
            **{k: (runtime or {}).get(k) for k in ("service", "pipeline", "dependencies")}}
    (grader_dir / "_grader_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if scenario_type == "service":                       # local service grading: LocalDeps + replay backend
        for m in ("deps.py", "replay.py", "runner.py"):
            s = ENGINE / m
            if s.exists():
                shutil.copy(s, grader_dir / m)
    for mod, dst in (("nfr_score.py", "nfr_score.py"), ("_grade.py", "grade.py")):   # Phase C scorer
        s = ENGINE / mod
        if s.exists():
            shutil.copy(s, grader_dir / dst)
    return {"n_tests": n, "n_smoke": n_smoke, "n_security": n_sec, "security_by_metric": sec_by_metric}
