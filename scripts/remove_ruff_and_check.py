import json, sys, pathlib, importlib, inspect
root = pathlib.Path(r"D:\code-bench")
mp = root / "dataset" / "pilot-v2.manifest.json"
m = json.loads(mp.read_text(encoding="utf-8"))
before = len(m["repos"])
m["repos"] = [r for r in m["repos"] if r["id"] != "astral-sh-ruff"]
mp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"pilot-v2 repos: {before} -> {len(m['repos'])}  (removed astral-sh-ruff)")
for d in ("engine", "agent", "stages", "."):
    sys.path.insert(0, str(root / d))
for mod in ("client", "stage0_ingest", "config", "orchestrate"):
    importlib.import_module(mod)
import client, stage0_ingest
print("CODEX_REASONING_EFFORT =", client.CODEX_REASONING_EFFORT)
print("build timeout wired:", "build_timeout_s" in inspect.getsource(stage0_ingest.run))
print("repair loop wired:", "_agent_fix_dockerfile" in inspect.getsource(stage0_ingest.run))
