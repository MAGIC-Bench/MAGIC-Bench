"""Engine smoke: drive gron byte-exactly via subprocess, capture golden + coverage."""
import os, pathlib, shutil, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from runner import LocalRunner, Invocation
import classify, gocover

REPO = r"D:\code-bench\repos\gron"
BIN = r"D:\code-bench\bin\gron_cov.exe"
COVROOT = r"D:\code-bench\out\gron\_cov_smoke"

shutil.rmtree(COVROOT, ignore_errors=True); os.makedirs(COVROOT, exist_ok=True)
runner = LocalRunner(BIN, cover_root=COVROOT)

two = pathlib.Path(REPO, "testdata", "two.json").read_bytes()
obs = runner.run(Invocation(argv=["-m"], stdin=two))

print("exit:", obs.exit_code, "| timed_out:", obs.timed_out)
print("stdout (first 180 bytes):")
print(obs.stdout[:180].decode("utf-8", "replace"))
print("stderr:", obs.stderr[:120])

# freeze a golden the way the loop would: exit exact, stdout normalized (line endings)
spec = [
    {"field": "exit", "class": "exact"},
    {"field": "stdout", "class": "normalized", "rule": "crlf_lf"},
    {"field": "stdout", "class": "invariant", "rule": "regex:^json = \\{\\};"},
]
golden = classify.freeze_golden(obs, spec)
print("frozen assertions:", [ {k:v for k,v in g.items() if k!='value'} for g in golden ])

# grade the SAME observation against the golden -> must all pass
print("self-check:", classify.check(obs, golden))

# compare against the repo's own intent golden (two.gron) after line-ending normalization
want = pathlib.Path(REPO, "testdata", "two.gron").read_bytes()
print("matches repo testdata/two.gron:",
      classify.norm_apply("crlf_lf", obs.stdout) == classify.norm_apply("crlf_lf", want))

print("coverage from this single run:", gocover.percent([obs.cover_dir]))
