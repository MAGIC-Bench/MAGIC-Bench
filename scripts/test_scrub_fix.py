"""Verify the de-identification fixes: dict-binary token extraction, short-token over-scrub guard,
and golden (assertion value + rule) scrub at packaging."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
for sub in ("engine", "stages", "."):
    sys.path.insert(0, str(ROOT / sub))
import deident, pytest_emit

fails = []
def chk(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

# --- dict-shaped binary (the candidate-doc leak root cause) ---
ot = deident.identity_tokens("github.com/ogen-go/ogen", {"primary": "ogen", "additional": ["jschemagen"]})
chk("dict binary: jschemagen tokenized", "jschemagen" in ot)
chk("dict binary: ogen tokenized", "ogen" in ot)
nt = deident.identity_tokens("bee-san-name-that-hash",
                             {"primary": "nth", "aliases": ["name-that-hash"],
                              "module_entrypoint": "python3 -m name_that_hash"})
chk("dict: name-that-hash tokenized", "name-that-hash" in nt)
chk("dict: name_that_hash tokenized", "name_that_hash" in nt)
chk("dict: nth tokenized", "nth" in nt)
chk("jschemagen scrubbed from doc", "jschemagen" not in deident.scrub_text("call jschemagen --target x", ot).lower())
chk("name-that-hash scrubbed from doc", "name-that-hash" not in deident.scrub_text("run name-that-hash -t md5", nt).lower())

# --- short-token over-scrub guard (com/sq/jd/nth must NOT corrupt unrelated words) ---
gt = deident.identity_tokens("github.com/josephburnett/jd", "jd")
chk("'com' not a token (NAME_STOP) -> 'command' intact", "command" in deident.scrub_text("run the command line", gt))
chk("short 'jd' word-bound -> 'jdk' intact", "jdk" in deident.scrub_text("install the jdk", gt))
chk("standalone 'jd' IS scrubbed", deident.scrub_text("the jd tool", gt) == "the app tool")
st = deident.identity_tokens("neilotoole/sq", "sq")
chk("short 'sq' word-bound -> 'sqlite' intact", "sqlite" in deident.scrub_text("uses sqlite backend", st))
mt = deident.identity_tokens("x/nth", "nth")
chk("short 'nth' word-bound -> 'month' intact", "month" in deident.scrub_text("every month", mt))

# --- longer token still substring (camelCase) ---
yt = deident.identity_tokens("adrienverge-yamllint", "yamllint")
chk("long 'yamllint' substring -> camelCase caught", "yamllint" not in deident.scrub_text("yamllintRun()", yt).lower())

# --- golden scrub at packaging (value + invariant rule) ---
jt = deident.identity_tokens("github.com/josephburnett/jd", "jd")
case = {"assertions": [
    {"field": "stdout", "class": "invariant", "rule": "regex:^jd version .+"},
    {"field": "stdout", "class": "exact", "value": {"utf8": "usage: jd [options]"}},
    {"field": "exit", "class": "invariant", "rule": "eq_int:0"},
], "observed": {"stdout_preview": "jd version 1.0"}}
sc = pytest_emit._scrub_case(case, jt)
chk("golden invariant RULE scrubbed", "jd" not in sc["assertions"][0]["rule"] and "app version" in sc["assertions"][0]["rule"])
chk("golden exact VALUE scrubbed", "jd" not in sc["assertions"][1]["value"]["utf8"] and "usage: app" in sc["assertions"][1]["value"]["utf8"])
chk("non-name rule untouched", sc["assertions"][2]["rule"] == "eq_int:0")

print("\n== FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
