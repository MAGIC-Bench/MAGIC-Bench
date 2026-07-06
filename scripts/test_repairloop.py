"""Verify the stage6 review->repair loop wiring + the content-coverage anti-gaming guard."""
import sys, pathlib, json, tempfile, shutil
ROOT = pathlib.Path(r"D:\code-bench-v2")
for s in ("engine", "agent", "stages", "."):
    sys.path.insert(0, str(ROOT / s))
import gates, orchestrate, agent_stages

fails = []
def ck(n, c):
    print(("OK   " if c else "FAIL ") + n)
    if not c:
        fails.append(n)

# 1) content-coverage counts exact/normalized + invariant(regex/eq_int/valid_json) on content fields
d = pathlib.Path(tempfile.mkdtemp()); td = d / "05_tests"; td.mkdir()
def case(name, ass): (td / f"{name}.json").write_text(json.dumps({"id": name, "assertions": ass}), encoding="utf-8")
case("c1", [{"field": "exit", "class": "exact", "value": {"int": 0}}])               # exit only -> NO
case("c2", [{"field": "stdout", "class": "exact", "value": {"utf8": "x"}}])          # exact content -> YES
case("c3", [{"field": "stdout", "class": "invariant", "rule": "regex:FURB\\d+"}])    # invariant:regex -> YES
case("c4", [{"field": "stdout", "class": "ignored"}])                                # ignored -> NO
r = gates._content_coverage_ratio(d)
ck(f"content-coverage ratio = 2/4 = 0.5 (got {r})", abs(r - 0.5) < 1e-9)

# 2a) gate_stage6 PASSES at exactly 50% coverage (boundary) when open_critical=0
(d / "06_adversarial.json").write_text(json.dumps({"open_critical": 0, "findings": []}), encoding="utf-8")
ok, msg = gates.gate_stage6(d)
ck("gate_stage6 passes at 50% coverage + open_critical=0", ok)

# 2b) gate_stage6 anti-gaming: open_critical=0 but coverage < 50% -> FAIL
d2 = pathlib.Path(tempfile.mkdtemp()); td2 = d2 / "05_tests"; td2.mkdir()
def case2(name, ass): (td2 / f"{name}.json").write_text(json.dumps({"id": name, "assertions": ass}), encoding="utf-8")
case2("a", [{"field": "stdout", "class": "exact", "value": {"utf8": "x"}}])   # 1 content
case2("b", [{"field": "stdout", "class": "ignored"}])
case2("c", [{"field": "exit", "class": "exact", "value": {"int": 0}}])
case2("e", [{"field": "stdout", "class": "ignored"}])                          # ratio = 1/4 = 0.25
(d2 / "06_adversarial.json").write_text(json.dumps({"open_critical": 0, "findings": []}), encoding="utf-8")
ok, msg = gates.gate_stage6(d2)
ck("gate_stage6 fails when repair gutted coverage (<50%)", not ok and "content" in (msg or ""))
shutil.rmtree(d2, ignore_errors=True)

# 3) repair driver: agent_stages.repair_stage6 exists + skips when no critical findings (no agent call)
ck("repair_stage6 exists", hasattr(agent_stages, "repair_stage6"))
agent_stages.repair_stage6("/x", d, {}, "stub", [{"severity": "major"}])   # no critical -> returns, no error

# 4) stub stage6 loop: writes 06_adversarial open_critical=0, repair_attempts=0, returns ok
ro = pathlib.Path(tempfile.mkdtemp())
ok, err = orchestrate._run_stage6("/nonexistent_repo", ro, {}, "stub")
adv = json.loads((ro / "06_adversarial.json").read_text(encoding="utf-8"))
ck("stub stage6 loop returns ok", ok and err is None)
ck("stub stage6 open_critical=0", adv.get("open_critical") == 0)
ck("stub stage6 repair_attempts recorded=0", adv.get("repair_attempts") == 0)

shutil.rmtree(d, ignore_errors=True); shutil.rmtree(ro, ignore_errors=True)
print("\nFAILS:", fails or "none")
sys.exit(1 if fails else 0)
