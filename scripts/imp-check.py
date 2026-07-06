import sys, pathlib
root = pathlib.Path(r"D:\code-bench")
for d in ("engine", "agent", "stages", "."):
    sys.path.insert(0, str(root / d))
import importlib
for m in ("stage0_ingest", "client", "dockermirror", "config", "orchestrate"):
    importlib.import_module(m)
import stage0_ingest
print("imports OK; stage0_ingest._agent_fix_dockerfile:", hasattr(stage0_ingest, "_agent_fix_dockerfile"))
