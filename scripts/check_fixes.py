import sys, pathlib, importlib, py_compile, tempfile, traceback
root = pathlib.Path(r"D:\code-bench")
for d in ("engine", "agent", "stages"):
    sys.path.insert(0, str(root / d))
sys.path.insert(0, str(root))

bad = 0
mods = ["classify", "runner", "replay", "pytest_emit", "harness", "grade", "deps",
        "coverage", "gocover", "config", "gates", "dockermirror", "cli_gen", "record_replay",
        "agent_stages", "client", "candidate",
        "stage0_ingest", "stage5_loop", "stage7_verify", "stage8_package",
        "orchestrate", "run_dataset"]
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        bad += 1
        print("IMPORT FAIL", m, repr(e))
        traceback.print_exc()

import runner, replay, agent_stages, pytest_emit
print("runner._docker_user_args() ->", runner._docker_user_args())   # [] on Windows (no getuid)
print("replay imported helper:", hasattr(replay, "_docker_user_args"))
print("CONTRACT:", {k: v[0] for k, v in agent_stages.CONTRACT.items()})
assert agent_stages.CONTRACT["service"][0] == "02_contract.openapi.json"
assert agent_stages.CONTRACT["pipeline"][0] == "02_contract.io.json"

# regenerate goawk's grader to a temp dir and compile the generated python (validates the conftest edit)
gd = pathlib.Path(tempfile.mkdtemp()) / "grader"
n = pytest_emit.emit(root / "out" / "benhoyt-goawk", gd, "cli")
print("emit regenerated", n, "cases")
for f in ("conftest.py", "test_blackbox.py", "_assert.py"):
    py_compile.compile(str(gd / f), doraise=True)
    print("  compiled OK:", f)
# confirm the --user line made it into the generated conftest
conf = (gd / "conftest.py").read_text(encoding="utf-8")
print("conftest has --user fix:", "--user" in conf and "getuid" in conf)
print("=== RESULT:", "ALL PASS" if bad == 0 else f"{bad} IMPORT FAILS")
