"""在服务器上实跑 LocalDeps:起 pg/mysql/redis -> 建表插数 -> reset -> 验空 -> stop。"""
import pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "engine"))
import deps

def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)

specs = [
    {"kind": "postgres", "env": "DATABASE_URL", "db_name": "appdb"},
    {"kind": "mysql", "env": "MYSQL_URL", "db_name": "appdb"},
    {"kind": "redis", "env": "REDIS_URL"},
]
d = deps.LocalDeps(specs)
fails = []
try:
    env = d.start()
    print("ENV 注入:", env)

    # postgres
    try:
        pgp = str(d.ports["postgres"])
        sh("psql", "-h", "127.0.0.1", "-p", pgp, "-U", "postgres", "-d", "appdb",
           "-c", "CREATE TABLE t(x int); INSERT INTO t VALUES (1),(2);")
        b = sh("psql", "-h", "127.0.0.1", "-p", pgp, "-U", "postgres", "-d", "appdb", "-tAc", "SELECT count(*) FROM t").stdout.strip()
        d.reset()
        a = sh("psql", "-h", "127.0.0.1", "-p", pgp, "-U", "postgres", "-d", "appdb", "-tAc", "SELECT count(*) FROM t").stdout.strip()
        ok = (b == "2" and a == "0")
        print(f"postgres: 插入后={b} reset后={a}  {'OK' if ok else 'FAIL'}")
        if not ok: fails.append("postgres")
    except Exception as e:
        print("postgres FAIL:", repr(e)[:200]); fails.append("postgres")

    # mysql
    try:
        mp = str(d.ports["mysql"])
        sh("mysql", "-h", "127.0.0.1", "-P", mp, "-uroot", "appdb", "-e", "CREATE TABLE t(x int); INSERT INTO t VALUES (1),(2);")
        b = sh("mysql", "-h", "127.0.0.1", "-P", mp, "-uroot", "appdb", "-Nse", "SELECT count(*) FROM t").stdout.strip()
        d.reset()
        a = sh("mysql", "-h", "127.0.0.1", "-P", mp, "-uroot", "appdb", "-Nse", "SELECT count(*) FROM t").stdout.strip()
        ok = (b == "2" and a == "0")
        print(f"mysql: 插入后={b} reset后={a}  {'OK' if ok else 'FAIL'}")
        if not ok: fails.append("mysql")
    except Exception as e:
        print("mysql FAIL:", repr(e)[:200]); fails.append("mysql")

    # redis
    try:
        rp = str(d.ports["redis"])
        sh("redis-cli", "-p", rp, "set", "k", "v")
        b = sh("redis-cli", "-p", rp, "get", "k").stdout.strip()
        d.reset()
        a = sh("redis-cli", "-p", rp, "get", "k").stdout.strip()
        ok = (b == "v" and a == "")
        print(f"redis: set后={b!r} reset后={a!r}  {'OK' if ok else 'FAIL'}")
        if not ok: fails.append("redis")
    except Exception as e:
        print("redis FAIL:", repr(e)[:200]); fails.append("redis")
finally:
    d.stop()
    print("stopped + cleaned")

print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
