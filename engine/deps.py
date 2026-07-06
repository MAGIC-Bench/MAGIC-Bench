"""External dependency provisioning + per-test state reset (databases & caches).

Some repos need a DB/cache at RUNTIME (not build time). We start sidecar containers on
a shared docker network, point the SUT at them via env vars, and RESET their state
BEFORE EVERY TEST CASE so no test pollutes the next. The SAME policy is used at exam
time (capturing golden from the original) and at grading time (running a candidate).

Kinds (only these two categories, per the dataset):
  database: postgres, mysql      cache: redis, memcached

reset() wipes data but keeps the schema and the SUT's live connections (TRUNCATE all
tables / FLUSHALL), so the SUT stays up across tests (fast). Build time never needs the
DB/cache — only runtime does.
"""
from __future__ import annotations

import subprocess
import time

DEFAULT_IMAGES = {
    "postgres": "postgres:16-alpine", "mysql": "mysql:8", "mongodb": "mongo:7",
    "redis": "redis:7-alpine", "memcached": "memcached:1.6-alpine",
}

# TRUNCATE every table in the public schema, keep the schema itself.
_PG_TRUNCATE = ("DO $$ DECLARE r RECORD; BEGIN "
                "FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname='public') LOOP "
                "EXECUTE 'TRUNCATE TABLE '||quote_ident(r.tablename)||' RESTART IDENTITY CASCADE'; "
                "END LOOP; END $$;")


class Deps:
    """Lifecycle: start() once per session -> reset() before each test -> stop() at end."""

    def __init__(self, specs, network, docker="docker"):
        self.specs = specs or []          # [{kind, env, image?, db_name?}]
        self.network = network
        self.docker = docker
        self.names = {}                   # kind -> container name
        self.env = {}                     # SUT env var -> connection URL

    def _d(self, args, **kw):
        return subprocess.run([self.docker, *args], capture_output=True, text=True, **kw)

    def start(self) -> dict:
        if not self.specs:
            return {}
        self._d(["network", "create", self.network])
        for s in self.specs:
            kind, name = s["kind"], f"{self.network}-{s['kind']}"
            cmd = ["run", "-d", "--rm", "--name", name, "--network", self.network]
            if kind == "postgres":
                cmd += ["-e", "POSTGRES_PASSWORD=test", "-e", "POSTGRES_DB=" + s.get("db_name", "appdb")]
            elif kind == "mysql":
                cmd += ["-e", "MYSQL_ROOT_PASSWORD=test", "-e", "MYSQL_DATABASE=" + s.get("db_name", "appdb")]
            cmd += [s.get("image") or DEFAULT_IMAGES[kind]]
            self._d(cmd)
            self.names[kind] = name
            self.env[s["env"]] = self._conn(kind, name, s)
        self._wait_ready()
        return self.env

    def _conn(self, kind, host, s):
        db = s.get("db_name", "appdb")
        return {"postgres": f"postgres://postgres:test@{host}:5432/{db}?sslmode=disable",
                "mysql": f"mysql://root:test@{host}:3306/{db}",
                "mongodb": f"mongodb://{host}:27017/{db}",
                "redis": f"redis://{host}:6379",
                "memcached": f"{host}:11211"}[kind]

    def _wait_ready(self, timeout=90):
        deadline = time.time() + timeout
        for s in self.specs:
            while time.time() < deadline and not self._healthy(s["kind"], self.names[s["kind"]]):
                time.sleep(0.5)

    def _healthy(self, kind, name):
        if kind == "postgres":
            return self._d(["exec", name, "pg_isready", "-U", "postgres"]).returncode == 0
        if kind == "mysql":
            return self._d(["exec", name, "mysqladmin", "ping", "-uroot", "-ptest", "--silent"]).returncode == 0
        if kind == "redis":
            return "PONG" in self._d(["exec", name, "redis-cli", "ping"]).stdout
        if kind == "memcached":
            return self._d(["exec", name, "sh", "-c", "echo stats | nc -w1 localhost 11211"]).returncode == 0
        if kind == "mongodb":
            return self._d(["exec", name, "mongosh", "--quiet", "--eval", "db.runCommand({ping:1}).ok"]).returncode == 0
        return True

    def reset(self):
        """Wipe ALL state before a test case (prevents cross-test pollution)."""
        for s in self.specs:
            kind, name = s["kind"], self.names.get(s["kind"])
            if not name:
                continue
            db = s.get("db_name", "appdb")
            if kind == "postgres":
                self._d(["exec", name, "psql", "-U", "postgres", "-d", db, "-c", _PG_TRUNCATE])
            elif kind == "mysql":
                gen = (f"SELECT CONCAT('TRUNCATE TABLE `',table_name,'`;') FROM information_schema.tables "
                       f"WHERE table_schema='{db}'")
                self._d(["exec", name, "sh", "-c",
                         f"mysql -uroot -ptest -Nse \"{gen}\" {db} | "
                         f"mysql -uroot -ptest --init-command='SET FOREIGN_KEY_CHECKS=0' {db}"])
            elif kind == "mongodb":
                self._d(["exec", name, "mongosh", db, "--quiet", "--eval",
                         "db.getCollectionNames().forEach(function(c){db.getCollection(c).deleteMany({})})"])
            elif kind == "redis":
                self._d(["exec", name, "redis-cli", "FLUSHALL"])
            elif kind == "memcached":
                self._d(["exec", name, "sh", "-c", "echo flush_all | nc -w1 localhost 11211"])

    def stop(self):
        for name in self.names.values():
            self._d(["stop", name])
        if self.specs:
            self._d(["network", "rm", self.network])


# ───────────────────────── LOCAL (no-docker) deps ─────────────────────────
import os
import pathlib
import shutil
import socket
import tempfile


def _free_port(start):
    p = start
    for _ in range(300):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                p += 1
    return start


class LocalDeps:
    """No-docker equivalent of Deps: runs postgres / mysql / redis as NATIVE local processes on
    unique 127.0.0.1 ports, injects connection URLs via env vars, TRUNCATE/FLUSHALL-resets per test,
    and tears down at the end. Same interface as Deps (start/reset/stop/.env) so the grader can pick
    either by runtime mode. mongodb/memcached aren't installed on this host -> start() raises a clear
    error naming the missing binary."""

    SUPPORTED = {"postgres", "mysql", "redis"}

    def __init__(self, specs, root=None):
        self.specs = specs or []
        self.root = pathlib.Path(root or tempfile.mkdtemp(prefix="localdeps_"))
        self.base = 20000 + (os.getpid() % 20000)
        self.dbuser = "dbrunner"   # postgres refuses root -> run it as this unprivileged user
        self.procs = {}        # kind -> (Popen | None)  (postgres is pg_ctl-managed by datadir)
        self.dirs = {}         # kind -> datadir
        self.ports = {}        # kind -> port
        self.env = {}          # SUT env var -> connection URL

    def _run(self, args, **kw):
        return subprocess.run(args, capture_output=True, text=True, **kw)

    def _require(self, *bins):
        for b in bins:
            if not shutil.which(b):
                raise RuntimeError(f"LocalDeps: 缺二进制 '{b}'（这台机没装该 DB）")

    def _ensure_dbuser(self):
        if self._run(["id", self.dbuser]).returncode != 0:
            self._run(["useradd", "-M", "-s", "/bin/bash", self.dbuser])

    def _ru(self, cmd):
        """Run as the unprivileged db user (postgres refuses root). Resolve the binary to an absolute
        path and whitelist PATH/LD_LIBRARY_PATH so the conda postgres + its libs are still found."""
        binpath = shutil.which(cmd[0]) or cmd[0]
        return ["runuser", "--whitelist-environment=PATH,LD_LIBRARY_PATH", "-u", self.dbuser, "--",
                binpath, *cmd[1:]]

    def start(self) -> dict:
        for s in self.specs:
            kind, db = s["kind"], s.get("db_name", "appdb")
            if kind not in self.SUPPORTED:
                raise RuntimeError(f"LocalDeps: 暂不支持 '{kind}'（本机未装 mongod/memcached）")
            getattr(self, f"_start_{kind}")(s, db)
        self._wait_ready()
        return self.env

    # ---- postgres ----
    def _start_postgres(self, s, db):
        self._require("initdb", "pg_ctl", "createdb", "psql")
        self._ensure_dbuser()
        os.chmod(self.root, 0o755)                         # let dbuser traverse the root-owned tmp dir
        port = self.ports["postgres"] = _free_port(self.base)
        d = self.dirs["postgres"] = self.root / "pg"
        d.mkdir(parents=True, exist_ok=True)
        self._run(["chown", "-R", self.dbuser, str(d)])
        r = self._run(self._ru(["initdb", "-D", str(d), "-U", "postgres",
                                "--auth-local=trust", "--auth-host=trust"]))
        if r.returncode != 0:
            raise RuntimeError("initdb failed: " + (r.stderr or r.stdout)[-300:])
        opts = f"-p {port} -k {d} -c listen_addresses=127.0.0.1"
        r = self._run(self._ru(["pg_ctl", "-D", str(d), "-o", opts, "-l", str(d / "server.log"), "-w", "start"]))
        if r.returncode != 0:
            raise RuntimeError("pg_ctl start failed: " + (r.stderr or r.stdout)[-300:])
        self._run(["createdb", "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", db])
        self.env[s["env"]] = f"postgres://postgres@127.0.0.1:{port}/{db}?sslmode=disable"

    # ---- mysql ----
    def _start_mysql(self, s, db):
        self._require("mysqld", "mysql")
        port = self.ports["mysql"] = _free_port(self.base + 100)
        d = self.dirs["mysql"] = self.root / "mysql"
        d.mkdir(parents=True, exist_ok=True)
        sock = self.root / "mysql.sock"
        self._run(["mysqld", "--no-defaults", "--initialize-insecure", f"--datadir={d}"], check=True)
        self.procs["mysql"] = subprocess.Popen(
            ["mysqld", "--no-defaults", "--user=root", f"--datadir={d}", f"--port={port}", f"--socket={sock}",
             "--bind-address=127.0.0.1", f"--pid-file={self.root / 'mysql.pid'}",
             f"--log-error={d / 'err.log'}", f"--tmpdir={self.root}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._mysql_wait(port)
        self._run(["mysql", "-h", "127.0.0.1", "-P", str(port), "-uroot",
                   "-e", f"CREATE DATABASE IF NOT EXISTS `{db}`"])
        self.env[s["env"]] = f"mysql://root@127.0.0.1:{port}/{db}"

    def _mysql_wait(self, port, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if self._run(["mysqladmin", "-h", "127.0.0.1", "-P", str(port), "-uroot", "ping"]).returncode == 0:
                return
            time.sleep(0.5)

    # ---- redis ----
    def _start_redis(self, s, db):
        self._require("redis-server", "redis-cli")
        port = self.ports["redis"] = _free_port(self.base + 200)
        self.procs["redis"] = subprocess.Popen(
            ["redis-server", "--port", str(port), "--dir", str(self.root), "--save", "", "--appendonly", "no"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.env[s["env"]] = f"redis://127.0.0.1:{port}"

    def _wait_ready(self, timeout=60):
        end = time.time() + timeout
        for s in self.specs:
            kind = s["kind"]
            while time.time() < end and not self._healthy(kind):
                time.sleep(0.5)

    def _healthy(self, kind):
        p = self.ports.get(kind)
        if not p:
            return False
        if kind == "postgres":
            return self._run(["pg_isready", "-h", "127.0.0.1", "-p", str(p), "-U", "postgres"]).returncode == 0
        if kind == "mysql":
            return self._run(["mysqladmin", "-h", "127.0.0.1", "-P", str(p), "-uroot", "ping"]).returncode == 0
        if kind == "redis":
            return "PONG" in self._run(["redis-cli", "-p", str(p), "ping"]).stdout.upper()
        return True

    def reset(self):
        for s in self.specs:
            kind, db, p = s["kind"], s.get("db_name", "appdb"), self.ports.get(s["kind"])
            if not p:
                continue
            if kind == "postgres":
                self._run(["psql", "-h", "127.0.0.1", "-p", str(p), "-U", "postgres", "-d", db, "-c", _PG_TRUNCATE])
            elif kind == "mysql":
                gen = (f"SELECT CONCAT('TRUNCATE TABLE `',table_name,'`;') FROM information_schema.tables "
                       f"WHERE table_schema='{db}'")
                stmts = self._run(["mysql", "-h", "127.0.0.1", "-P", str(p), "-uroot", "-Nse", gen, db]).stdout
                if stmts.strip():
                    self._run(["mysql", "-h", "127.0.0.1", "-P", str(p), "-uroot",
                               "--init-command=SET FOREIGN_KEY_CHECKS=0", db], input=stmts)
            elif kind == "redis":
                self._run(["redis-cli", "-p", str(p), "FLUSHALL"])

    def stop(self):
        if "postgres" in self.dirs:
            self._run(self._ru(["pg_ctl", "-D", str(self.dirs["postgres"]), "-m", "fast", "stop"]))
        for kind, proc in self.procs.items():
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
        shutil.rmtree(self.root, ignore_errors=True)


def make_deps(specs, config):
    """Pick the deps provider by runtime mode: docker -> Deps (sidecar containers); else LocalDeps."""
    rt = (config or {}).get("runtime") or {"mode": "local"}
    if rt.get("mode") == "docker":
        return Deps(specs, network=f"net-{(config or {}).get('repo_id', 'x')}")
    return LocalDeps(specs)
