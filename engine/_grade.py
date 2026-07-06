#!/usr/bin/env python3
"""Candidate grader (Phase C runner) — emitted into 07_exam/grader/ as grade.py.

Builds a rich RUN REPORT by running the candidate over the suite (functional + security + smoke) with
per-case timing / peak-memory / crash flags, runs the applicable RLY/CMP run-modes, asks codex to score
the applicable STATIC metrics, then calls nfr_score.compute_scores and writes score.json.

  CANDIDATE_BIN=./my_impl   python grade.py
  (local mode; the candidate's own build script must have produced CANDIDATE_BIN first.)

Output score.json: { "build_ok", "功能分", "nfr_by_dimension": {dim: {metric: 1|0|None}} }.
"""
import base64, json, os, pathlib, shutil, subprocess, sys, tempfile, time, concurrent.futures as cf
import urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _assert import assert_all          # emitted alongside
import nfr_score                         # emitted alongside

CASES = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "cases").glob("*.json"))]
APPLICABLE = json.loads((HERE / "nfr_applicable.json").read_text(encoding="utf-8")).get("applicable", []) \
    if (HERE / "nfr_applicable.json").exists() else []
META = json.loads((HERE / "_grader_meta.json").read_text(encoding="utf-8")) if (HERE / "_grader_meta.json").exists() else {}
BIN = os.environ.get("CANDIDATE_BIN")
TIMEOUT = float(os.environ.get("CASE_TIMEOUT", "60"))
GNU_TIME = "/usr/bin/time" if os.path.exists("/usr/bin/time") else None


def _file_bytes(v):
    if isinstance(v, str):
        return base64.b64decode(v)
    return base64.b64decode(v["b64"]) if "b64" in v else v.get("text", "").encode("utf-8")


def _stdin(inp):
    if inp.get("stdin_b64"):
        return base64.b64decode(inp["stdin_b64"])
    return (inp.get("stdin") or "").encode("utf-8")


def run_one(case, rlimit_as_kb=None):
    """Run one cli case against CANDIDATE_BIN; return a rich result dict for the run report.
    rlimit_as_kb caps the candidate's address space (RLY4 resource-pressure mode)."""
    inp = case.get("input", {})
    argv = inp.get("argv", [])
    files = {k: _file_bytes(v) for k, v in inp.get("files", {}).items()}
    work = tempfile.mkdtemp(prefix="grade_")
    res = {"id": case.get("id"), "security_metric": case.get("security_metric"),
           "smoke": bool(case.get("smoke")), "latency_s": None, "peak_mem_mb": None,
           "crashed": False, "timed_out": False, "oom": False, "passed": False}
    try:
        before = {}
        for n, d in files.items():
            p = pathlib.Path(work, n); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(d); before[n] = d
        memf = os.path.join(work, ".mem")
        cmd = ([GNU_TIME, "-v", "-o", memf, BIN, *argv] if GNU_TIME else [BIN, *argv])
        env = dict(os.environ, TZ="UTC", LC_ALL="C", NO_COLOR="1")
        pre = None
        if rlimit_as_kb:                                      # RLY4: cap address space to pressure the candidate
            def pre():
                import resource
                b = int(rlimit_as_kb) * 1024
                resource.setrlimit(resource.RLIMIT_AS, (b, b))
        t0 = time.monotonic()
        try:
            p = subprocess.run(cmd, input=_stdin(inp), capture_output=True, cwd=work, env=env,
                               timeout=TIMEOUT, preexec_fn=pre)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            res["timed_out"] = True; res["latency_s"] = TIMEOUT; return res
        res["latency_s"] = time.monotonic() - t0
        res["crashed"] = rc < 0 and rc not in (-9,)          # killed by a signal (segv/abrt) = crash
        res["oom"] = rc in (-9, 137)                          # SIGKILL / 137 ~= OOM-kill
        if GNU_TIME and os.path.exists(memf):                 # best-effort peak RSS (kB) -> MB
            for line in pathlib.Path(memf).read_text(errors="replace").splitlines():
                if "Maximum resident set size" in line:
                    try: res["peak_mem_mb"] = int(line.split(":")[-1].strip()) / 1024.0
                    except Exception: pass
        out_files = {}
        for fp in pathlib.Path(work).rglob("*"):
            if fp.is_file():
                rel = str(fp.relative_to(work)).replace("\\", "/")
                if rel == ".mem": continue
                data = fp.read_bytes()
                if before.get(rel) != data:
                    out_files[rel] = data
        obs = {"exit": rc, "stdout": p.stdout, "stderr": p.stderr, "files": out_files}
        try:
            assert_all(obs, case.get("assertions", []))
            res["passed"] = True
        except AssertionError:
            res["passed"] = False
        return res
    finally:
        shutil.rmtree(work, ignore_errors=True)


def static_scores(applicable):
    """Score the STATIC NFR metrics on candidate source (0/1) with codex (low effort).
    【解耦+缓存】静态分只读源码、与 launch/运行无关 → 每份卷算一次就缓存到 <submission>/static.json,
    任何重判(如功能侧 bug 重跑)直接复用、不再调 codex。不降级:重试 STATIC_RETRIES 次。"""
    statics = [m for m in applicable if m.get("kind") == "static"]
    src = os.environ.get("CANDIDATE_SRC")
    if not statics or not src:
        return {}
    ids = {m["metric_id"] for m in statics}
    cache = os.path.join(os.path.dirname(src.rstrip("/")), "static.json")   # 持久(submission 目录),跨重判复用
    try:
        c = json.load(open(cache, encoding="utf-8"))
        if ids <= set(c):                       # 缓存已覆盖所有需要的静态指标 → 复用,跳过 codex
            return {k: c[k] for k in ids}
    except Exception:
        pass
    if not shutil.which("codex"):
        return {}
    spec = "\n".join(f"- {m['metric_id']} ({m.get('name','')}): {m.get('desc','')}" for m in statics)
    prompt = ("Read the candidate project's source at the path in CANDIDATE_SRC. For EACH static NFR metric "
              "below, score it 0 or 1 strictly per its rule (1 = satisfied, 0 = violated). Output ONLY a JSON "
              f"object mapping metric_id to 0/1, nothing else.\nCANDIDATE_SRC={src}\nMetrics:\n{spec}")
    for _attempt in range(int(os.environ.get("STATIC_RETRIES", "3"))):
        try:
            # --sandbox danger-full-access:容器里 bwrap 坏,默认 sandbox 起不来;此调用只 READS 源码。
            p = subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "danger-full-access",
                                "--color", "never", "-c", "model_reasoning_effort=low", prompt],
                               capture_output=True, text=True,
                               timeout=float(os.environ.get("STATIC_TIMEOUT", "300")))
            txt = p.stdout
            a, b = txt.rfind("{"), txt.rfind("}")
            obj = json.loads(txt[a:b + 1]) if a >= 0 and b > a else {}
            scored = {k: (1 if v else 0) for k, v in obj.items() if k in ids}
            if scored:                          # 打出分了:存缓存 + 返回(空 → 重试,不降级)
                try:
                    json.dump(scored, open(cache, "w", encoding="utf-8"))
                except Exception:
                    pass
                return scored
        except Exception:
            pass
    return {}


def _http(method, url, body=None, timeout=10):
    """Return (status|None, body_bytes). status None => connection refused / hang / crash (NOT graceful)."""
    data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:                   # a clear HTTP error IS graceful
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()


class LocalService:
    """Run the candidate as a local server (local mode, no docker). Reads META['service']:
    {port, health_path, args, ready_timeout}. Deps (DB/cache) are assumed already up."""
    def __init__(self):
        svc = META.get("service", {})
        self.port = int(os.environ.get("CANDIDATE_PORT", svc.get("port", 8080)))
        self.health = svc.get("health_path", "/health")
        self.args = svc.get("args", [])
        self.ready_t = float(svc.get("ready_timeout", 30))
        self.proc = None

    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        env = dict(os.environ, PORT=str(self.port), TZ="UTC", LC_ALL="C")
        self.proc = subprocess.Popen([BIN, *self.args], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.monotonic()
        while time.monotonic() - t0 < self.ready_t:
            if self.proc.poll() is not None:
                return False
            st, _ = _http("GET", self.base() + self.health, timeout=3)
            if st and st < 500:
                return True
            time.sleep(0.3)
        return False

    def probe(self):                                     # smoke: health responds < 500 (process alive + serving)
        st, _ = _http("GET", self.base() + self.health, timeout=5)
        return bool(st) and st < 500

    def terminate(self):
        if self.proc:
            self.proc.terminate()
            try: self.proc.wait(timeout=10)
            except Exception: self.proc.kill()

    def restart(self):                                   # keep the data dir (dirty restart)
        self.terminate(); return self.start()

    def kill(self):                                      # abrupt SIGKILL
        if self.proc:
            self.proc.kill(); self.proc.wait(timeout=10)

    stop = terminate


def _cmp2_schema(svc):
    """CMP2: validate sample responses against the contract schema. None unless a schema + service cases
    with endpoints are present (jsonschema must be importable)."""
    schema = META.get("contract_schema") or META.get("openapi")
    cases = [c for c in CASES if c.get("input", {}).get("http")]
    if not schema or not cases:
        return None
    try:
        import jsonschema
    except Exception:
        return None
    for c in cases[:8]:
        h = c["input"]["http"]
        st, body = _http(h.get("method", "GET"), svc.base() + h.get("path", "/"), h.get("body"))
        if st is None:
            return False
        try:
            jsonschema.validate(json.loads(body or b"null"), schema)
        except Exception:
            return False
    return True


def _rly3_db_fault(svc):
    """RLY3: stop the DB dep mid-flight, hit the service, expect a graceful HTTP error (not refused/crash);
    then restore. None unless META supplies db_stop/db_start hooks (local dep control)."""
    stop_cmd = META.get("db_stop"); start_cmd = META.get("db_start")
    probe = META.get("service", {}).get("probe_path", svc.health)
    if not stop_cmd or not start_cmd:
        return None
    subprocess.run(stop_cmd, shell=True, timeout=60)
    try:
        st, _ = _http("GET", svc.base() + probe, timeout=10)
        graceful = st is not None and (svc.proc.poll() is None)   # clear error + main process still alive
    finally:
        subprocess.run(start_cmd, shell=True, timeout=60)
    return bool(graceful)


def service_modes(ids):
    """RLY2/RLY6/RLY3/CMP2 against a live local service. Keys omitted (=> metric None) when the service
    can't start or the mode's config is absent."""
    out = {}
    if not any(m in ids for m in ("RLY2", "RLY6", "RLY3", "CMP2")):
        return out
    svc = LocalService()
    if not svc.start():                                  # candidate service won't come up -> can't run these
        svc.stop(); return out
    try:
        if "RLY2" in ids:                                # dirty restart x3, health must return each time
            ok = True
            for _ in range(3):
                if not svc.restart() or not svc.probe():
                    ok = False; break
            out["RLY2"] = {"passed": ok}
        if "RLY6" in ids:                                # force-kill then restart, health must return
            svc.kill(); out["RLY6"] = {"passed": bool(svc.start() and svc.probe())}
        if "CMP2" in ids:
            v = _cmp2_schema(svc)
            if v is not None: out["CMP2"] = {"passed": v}
        if "RLY3" in ids:
            v = _rly3_db_fault(svc)
            if v is not None: out["RLY3"] = {"passed": v}
    finally:
        svc.stop()
    return out


def run_modes(applicable):
    """Applicable RLY/CMP run-modes (label-driven). Returns {metric_id: {"passed": bool}}.
    Universal/CLI: RLY1 repeat, RLY5 concurrent, RLY4 resource-limit. Service-only (scenario=service):
    RLY2 dirty-restart, RLY6 force-kill, RLY3 DB-disconnect, CMP2 contract schema -> service_modes()."""
    ids = {m["metric_id"] for m in applicable}
    modes = {}
    func = [c for c in CASES if not c.get("security_metric") and not c.get("smoke")]
    sample = func[:8] or func
    if "RLY1" in ids:                                     # long/repeat: run sample x3, all-pass + no crash
        ok = True
        for _ in range(3):
            for c in sample:
                r = run_one(c)
                if not r["passed"] or r["crashed"] or r["timed_out"]:
                    ok = False; break
            if not ok: break
        modes["RLY1"] = {"passed": ok}
    if "RLY5" in ids:                                     # concurrency: run sample in parallel, no crash/deadlock
        ok = True
        with cf.ThreadPoolExecutor(max_workers=min(8, len(sample) or 1)) as ex:
            for r in ex.map(run_one, sample * 2):
                if r["crashed"] or r["timed_out"] or r["oom"]:
                    ok = False
        modes["RLY5"] = {"passed": ok}
    if "RLY4" in ids:                                     # resource pressure: tight memory cap -> graceful (no signal crash)
        cap = int(os.environ.get("RLY4_MEM_KB", "262144"))   # 256 MB default
        ok = True
        for c in (sample[:4] or sample):
            r = run_one(c, rlimit_as_kb=cap)
            if r["crashed"] or r["oom"]:                  # a clean nonzero exit under pressure is graceful (pass)
                ok = False; break
        modes["RLY4"] = {"passed": ok}
    if META.get("scenario_type") == "service":           # RLY2/RLY6/RLY3/CMP2 need a live service
        modes.update(service_modes(ids))
    return modes


def run_service_cases():
    """SERVICE grading: run cases against the candidate SERVICE via replay.LocalServiceBackend
    (starts the candidate service once + LocalDeps DB, resets DB before each case, replays the HTTP
    steps). Build/start gate: if the service never comes up, the rest fail (crashed) -> build_ok=False.
    NOTE: end-to-end-untested until a real service exam exists; reuses the proven docker ServiceBackend
    HTTP/assert logic via LocalServiceBackend."""
    import replay
    config = {"scenario_type": "service", "service": META.get("service", {}),
              "dependencies": META.get("dependencies", []), "launch": [BIN], "runtime": {"mode": "local"}}
    backend = replay.LocalServiceBackend()
    results, started, dead = [], False, False
    for c in CASES:
        res = {"id": c.get("id"), "security_metric": c.get("security_metric"), "smoke": bool(c.get("smoke")),
               "passed": False, "latency_s": None, "peak_mem_mb": None,
               "crashed": False, "timed_out": False, "oom": False}
        if not dead:
            try:
                t = time.monotonic()
                o = backend.run(None, [], c.get("input", {}), config)   # _ensure(svc+deps) + reset + replay
                started = True
                res["latency_s"] = time.monotonic() - t
                obs = {"exit": o.exit_code, "stdout": o.stdout, "stderr": o.stderr,
                       "files": o.out_files, "http": (o.extra or {}).get("http")}
                try:
                    assert_all(obs, c.get("assertions", []))
                    res["passed"] = True
                except AssertionError:
                    res["passed"] = False
            except Exception:
                if not started:                       # service never came up -> build/start gate fails all
                    dead = True
                res["crashed"] = not started
        results.append(res)
    try:
        backend.teardown()
    except Exception:
        pass
    return results


def main():
    if not BIN:
        print("set CANDIDATE_BIN=<candidate binary>", file=sys.stderr); sys.exit(2)
    scen = META.get("scenario_type", "cli")
    t0 = time.monotonic()
    results = run_service_cases() if scen == "service" else [run_one(c) for c in CASES]
    total_time = time.monotonic() - t0
    smoke = [r for r in results if r["smoke"]]
    build_ok = bool(smoke) and all(r["passed"] for r in smoke) or (not smoke)   # no smoke -> assume built
    report = {"build_ok": build_ok, "total_time_s": total_time, "cases": results,
              "modes": run_modes(APPLICABLE) if build_ok else {}}
    # 静态分只在 build_ok 时算(build 门会把失败卷的所有 NFR 归零,给失败卷算静态是浪费 codex)。
    # 但 static_scores 内部带【缓存】:每份卷算一次存 static.json → 之后任何重判(如功能侧 bug 重跑)直接复用、不再调 codex。
    statics = static_scores(APPLICABLE) if build_ok else {}
    score = nfr_score.compute_scores(report, APPLICABLE, static_results=statics)
    (HERE / "score.json").write_text(json.dumps(score, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(score, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
