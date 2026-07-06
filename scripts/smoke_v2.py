"""v2 fix smoke: import every edited module, assert the new wiring, and run a full Stage-8 render
on a synthetic repo_out to verify the candidate package is complete + de-identified + scrubbed."""
import importlib, json, pathlib, sys, tempfile, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
for sub in ("engine", "agent", "stages", "."):
    sys.path.insert(0, str(ROOT / sub))

fails = []
def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

# 1) imports
for m in ["gates", "stage5_loop", "stage7_verify", "stage8_package", "pytest_emit", "client",
          "candidate", "agent_stages", "orchestrate", "replay", "runner", "deps"]:
    try:
        importlib.import_module(m); print("OK   import", m)
    except Exception as e:
        print("FAIL import", m, "->", type(e).__name__, e); fails.append("import " + m)

import gates, stage8_package, candidate, stage7_verify, pytest_emit

# 2) wiring
check("gate_stage7 in GATES", 7 in gates.GATES)
check("stage7 mutation removed", not hasattr(stage7_verify, "mutation"))
check("candidate.assemble_spec exists", hasattr(candidate, "assemble_spec"))
check("stage8 helpers present", all(hasattr(stage8_package, f)
      for f in ("_scrub_contract", "_api_manual_md", "_brief_md", "_nfr_md")))
check("conftest emits ServiceSUT+PipelineSUT",
      "class ServiceSUT" in pytest_emit._CONFTEST and "class PipelineSUT" in pytest_emit._CONFTEST)
check("emit accepts runtime", "runtime" in pytest_emit.emit.__code__.co_varnames)

# 3) contract scrub (via shared deident tokens; incl. camelCase compound)
import deident
toks = deident.identity_tokens("adrienverge-yamllint", "yamllint")
sc = stage8_package._scrub_contract(
    {"binary": "yamllint", "usage": "yamllintRun [options] FILE", "contract_type": "cli",
     "flags": [{"long": "--strict", "doc": "use the yamllintCore engine"}]}, toks)
check("scrub replaces binary -> app", sc["binary"] == "app")
check("scrub removes name from values (incl camelCase)",
      "yamllint" not in json.dumps(sc, ensure_ascii=False).lower())

# 4) gate_stage1 brief + anti-cheat leak
tmp = pathlib.Path(tempfile.mkdtemp())
def w1(obj): (tmp / "01_repo-model.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
w1({"repo_id": "adrienverge-yamllint", "scenario_type": "cli", "public_surface": "x"})
check("gate_stage1 fails w/o candidate_brief", not gates.gate_stage1(tmp)[0])
w1({"repo_id": "adrienverge-yamllint", "scenario_type": "cli", "public_surface": "x",
    "candidate_brief": "A linter for yamllint files."})
check("gate_stage1 fails on repo-name leak", not gates.gate_stage1(tmp)[0])
w1({"repo_id": "adrienverge-yamllint", "scenario_type": "cli", "public_surface": "x",
    "candidate_brief": "A command-line checker that reports style issues in structured config documents."})
check("gate_stage1 passes a clean brief", gates.gate_stage1(tmp)[0])

# 5) gate_stage3 user_value + story format
def w3(mods, stories):
    (tmp / "03_modules.json").write_text(json.dumps({"modules": mods}, ensure_ascii=False), encoding="utf-8")
    (tmp / "03_user-stories.json").write_text(json.dumps({"stories": stories}, ensure_ascii=False), encoding="utf-8")
w3([{"id": "M1", "name": "Lint", "user_value": "users find errors early"}],
   [{"id": "S1", "modules": ["M1"], "prose": {"actor": "u", "precondition": "p", "trigger": "t",
     "expected": "e"}, "code": ["app x"]}])
check("gate_stage3 passes good modules+stories", gates.gate_stage3(tmp)[0])
w3([{"id": "M1", "name": "Lint"}],
   [{"id": "S1", "modules": ["M1"], "prose": {"actor": "u", "precondition": "p", "trigger": "t",
     "expected": "e"}, "code": ["app x"]}])
check("gate_stage3 fails on missing user_value", not gates.gate_stage3(tmp)[0])
w3([{"id": "M1", "name": "Lint", "user_value": "v"}],
   [{"id": "S1", "modules": ["M1"], "prose": {"actor": "u", "precondition": "", "trigger": "t",
     "expected": "e"}, "code": ["app x"]}])
check("gate_stage3 fails on incomplete story prose", not gates.gate_stage3(tmp)[0])

# gate_stage6: open_critical is a HARD ship-blocker
check("gate_stage6 in GATES", 6 in gates.GATES)
(tmp / "06_adversarial.json").write_text(json.dumps({"open_critical": 2, "findings": [{"issue": "x"}]}), encoding="utf-8")
check("gate_stage6 fails on open_critical>0", not gates.gate_stage6(tmp)[0])
(tmp / "06_adversarial.json").write_text(json.dumps({"open_critical": 0, "findings": []}), encoding="utf-8")
check("gate_stage6 passes on open_critical=0", gates.gate_stage6(tmp)[0])

# 6) full Stage-8 render
ro = pathlib.Path(tempfile.mkdtemp())
def wr(p, obj): (ro / p).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
wr("01_repo-model.json", {"repo_id": "adrienverge-yamllint", "scenario_type": "cli",
   "public_surface": "yamllint", "language": "python", "rewritable_languages": ["go", "rust"],
   "candidate_brief": "A command-line checker that flags style and consistency problems in structured "
                      "configuration documents and prints a report."})
wr("02_cli-contract.json", {"contract_type": "cli", "binary": "yamllint", "usage": "yamllint [opts] FILE",
   "flags": [{"long": "--strict", "short": "-s", "type": "bool", "doc": "fail on warnings"}],
   "exit_codes": {"0": "clean", "1": "problems"}, "io_contract": {"stdout": "report", "stderr": "errors"}})
# deliberately leak the tool/owner name in 03 + flags to prove the doc-scrub catches it
wr("03_modules.json", {"modules": [{"id": "M1", "name": "Run yamllint over a directory",
   "user_value": "lets you lint with the yamllint engine"}]})
wr("03_user-stories.json", {"stories": [{"id": "S1", "modules": ["M1"],
   "prose": {"actor": "dev", "precondition": "a file authored by adrienverge", "trigger": "invoke yamllint",
             "expected": "a report"}, "code": ["yamllint -c config.yaml file.yml"]}]})
wr("nfr-metrics.json", {"metrics": [{"id": "PERF4", "name": "限时正确通过", "dimension": "PERF",
   "kind": "runtime", "scoring": "binary", "desc": "600s 内 ≥70% 通过且无运行失败。"}]})
wr("04_nfr-labels.json", {"labels": [{"metric_id": "PERF4", "applies": True}], "applicable": ["PERF4"]})
(ro / "05_tests").mkdir()
(ro / "05_tests" / "t1.json").write_text(json.dumps({"id": "t1", "modules": ["M1"],
   "input": {"argv": ["FILE"]}, "assertions": [{"field": "exit", "class": "exact", "value": {"int": 0}}]}),
   encoding="utf-8")

rep = stage8_package.run(ro, {"scenario_type": "cli"})
candf = set(rep["candidate_files"])
need = {"项目描述.md", "用户API使用手册.md", "功能模块文档.md", "用户行为示例文档.md",
        "非功能需求.md", "generation_language.txt", "prompt.md", "02_cli-contract.json"}
check("candidate package has all 8 files", need <= candf)
cand = ro / "07_exam" / "candidate"
check("generation_language = rewritable[0] (go)", (cand / "generation_language.txt").read_text().strip() == "go")
check("candidate contract scrubbed (no 'yamllint')",
      "yamllint" not in (cand / "02_cli-contract.json").read_text(encoding="utf-8"))
check("feature list has no M-id", "M1" not in (cand / "功能模块文档.md").read_text(encoding="utf-8"))
brief = (cand / "项目描述.md").read_text(encoding="utf-8")
check("项目描述 present + no repo name", "yamllint" not in brief and len(brief) > 20)
man = (cand / "用户API使用手册.md").read_text(encoding="utf-8")
check("API manual renders flags + no repo name", "--strict" in man and "yamllint" not in man)
# NO candidate-facing file may leak the tool name or owner (incl. the 03-derived docs)
leak_hits = []
for fp in cand.iterdir():
    if fp.is_file():
        low = fp.read_text(encoding="utf-8", errors="replace").lower()
        leak_hits += [f"{fp.name}:{bad}" for bad in ("yamllint", "adrienverge") if bad in low]
check("NO candidate file leaks tool/owner name", not leak_hits)
if leak_hits:
    print("   leaks:", leak_hits)
check("grader _grader_meta.json written", (ro / "07_exam" / "grader" / "_grader_meta.json").exists())

# 7) candidate.assemble_spec consumes the SAME package (unified, no divergent SPEC)
spec = pathlib.Path(tempfile.mkdtemp()) / "SPEC"
copied = candidate.assemble_spec(ro, spec, {"scenario_type": "cli"})
check("assemble_spec copies the canonical 8-file package", need <= set(copied))
check("assemble_spec does NOT leak 01_repo-model.json", "01_repo-model.json" not in copied)

shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(ro, ignore_errors=True)
print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
